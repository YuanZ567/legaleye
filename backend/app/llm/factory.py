"""LLM 工厂：四 provider 路由 + Fernet 解密 + LLMCallRecord 记账。

纪律（ARCHITECTURE 6.1/6.2 + 契约）：
- **禁止裸调 LLM**：业务层只允许经 `chat_completion` 发起调用；
- Key 以 Fernet 密文存 ModelConfig，经 `security.decrypt_secret` 解密后仅内存使用；
- 每次调用写 LLMCallRecord（L3 记账：tokens/cost/latency），供仪表盘聚合；
- 四 provider 路由：bailian/deepseek/openai 走 OpenAI 兼容接口（不同 base_url），
  anthropic 走 Anthropic 接口。

未配置 ModelConfig 时抛 LLMConfigError（不静默 fallback，避免隐藏配置问题）。
"""

import logging
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Provider
from app.core.exceptions import LLMError
from app.core.security import decrypt_secret
from app.core.sse import publish_token_usage
from app.models.model_config import LLMCallRecord, ModelConfig
from app.models.review_task import ReviewTask

logger = logging.getLogger(__name__)

# OpenAI 兼容接口的 base_url 路由（对齐架构 6.2）
PROVIDER_BASE_URLS: dict[Provider, str] = {
    Provider.BAILIAN: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    Provider.DEEPSEEK: "https://api.deepseek.com/v1",
    Provider.OPENAI: "https://api.openai.com/v1",
    Provider.MODELSCOPE: "https://api-inference.modelscope.cn/v1",
    Provider.ZHIPU: "https://open.bigmodel.cn/api/paas/v4",
    Provider.SILICONFLOW: "https://api.siliconflow.cn/v1",
}

# 魔搭社区环境变量名（key 优先从 DB ModelConfig 读，未配置时从 env 兜底；
# user-level env var 需用 Win32 注册表读取才能拿到，process 继承不到）
MODELSCOPE_ENV_KEY = "Modelscope_API_KEY"
# 智谱 BigModel 环境变量名（与魔搭同模式：env 兜底，不依赖 ModelConfig 表）
ZHIPU_ENV_KEY = "ZHIPU_API_KEY"
# 硅基流动环境变量名（同上，env 兜底）
SILICONFLOW_ENV_KEY = "SILICONFLOW_API_KEY"


def _read_user_env(name: str) -> str:
    """读取 Windows 用户级环境变量（HKCU\\Environment），处理 REG_EXPAND_SZ。

    常规 os.environ 只能拿到进程继承的 env（启动时快照），新设的用户级变量需重启进程才能用；
    这里直接读注册表 + 展开环境变量引用（如 %USERPROFILE%）。
    """
    import os
    import sys
    if sys.platform != "win32":
        return os.environ.get(name, "")
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
            value, reg_type = winreg.QueryValueEx(k, name)
        if reg_type == 1:  # REG_SZ
            return value
        if reg_type == 2:  # REG_EXPAND_SZ
            import ctypes
            buf = ctypes.create_unicode_buffer(2048)
            ctypes.windll.kernel32.ExpandEnvironmentStringsW(value, buf, 2048)
            return buf.value
        return value
    except (FileNotFoundError, OSError):
        return os.environ.get(name, "")

# 降级容错（ARCHITECTURE 6.4）：单次调用超时，失败重试 2 次（指数退避）
# 420s：智谱免费层 4.5-flash 评估长 prompt 实测响应可超 60s（2026-09-02）；
# 2026-09-05 d5 长 prompt 首次调用实测超 240s（触发降级→反思恶性循环），放宽到 420s
LLM_TIMEOUT_SECONDS = 420
LLM_MAX_RETRIES = 2
LLM_RETRY_BACKOFF = 2.0
# 429 限流退避更长（魔搭/百炼免费层并发限流；避免整批降级待补）
LLM_429_BACKOFF = 20.0


class LLMConfigError(LLMError):
    """模型配置缺失/解密失败。"""


def get_active_model_config(db: Session, provider: Provider) -> ModelConfig:
    """读取指定 provider 的活跃模型配置（未配置抛 LLMConfigError）。"""
    cfg = db.scalar(
        select(ModelConfig)
        .where(
            ModelConfig.provider == provider,
            ModelConfig.is_active.is_(True),
        )
        .order_by(ModelConfig.created_at.desc())
        .limit(1)
    )
    if cfg is None:
        raise LLMConfigError(
            f"未配置活跃的 {provider.value} 模型，请先配置", code="model_not_configured"
        )
    return cfg


def _build_openai_client(api_key: str, base_url: str) -> Any:
    """构造 OpenAI 兼容 client（bailian/deepseek/openai 共用），带 60s 超时。"""
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=base_url, timeout=LLM_TIMEOUT_SECONDS)


def _build_anthropic_client(api_key: str) -> Any:
    """构造 Anthropic client，带 60s 超时。"""
    import anthropic

    return anthropic.Anthropic(api_key=api_key, timeout=LLM_TIMEOUT_SECONDS)


def _record_call(
    *,
    db: Session,
    provider: Provider,
    model: str,
    node: str | None,
    task_id: Any | None,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
) -> None:
    """写 LLMCallRecord 记账（L3），并同步任务 token 用量 + SSE 推送。

    M10 修复：    此前只写 LLMCallRecord，ReviewTask.token_usage 永远为 0、
    tokenUsage SSE 事件从不发布 → 前端"已用 token"恒为 0。
    task_id 归一化为 UUID（调用方常传 str；LLMCallRecord.task_id 是 UUID 列）。
    """
    tid: uuid.UUID | None = None
    if task_id is not None:
        try:
            tid = task_id if isinstance(task_id, uuid.UUID) else uuid.UUID(str(task_id))
        except (ValueError, AttributeError, TypeError):
            tid = None
    db.add(
        LLMCallRecord(
            task_id=tid,
            node=node,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_est=0.0,  # 成本估算在 M4 后续按 provider 单价补充
            latency_ms=latency_ms,
        )
    )
    if tid is not None:
        try:
            task = db.get(ReviewTask, tid)
            if task is not None:
                task.token_usage = (task.token_usage or 0) + input_tokens + output_tokens
                # tokenUsage SSE 事件（契约 DATA_CONTRACT 3.3）：仅真实任务推送
                publish_token_usage(
                    str(tid),
                    provider=provider.value,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
        except Exception as exc:  # noqa: BLE001 — token 统计失败绝不影响审查主流程
            logger.warning("任务 token 用量同步失败（不影响调用）: %s", exc)
    db.commit()


def chat_completion(
    *,
    db: Session,
    provider: Provider,
    model: str | None,
    messages: list[dict],
    node: str | None = None,
    task_id: Any | None = None,
    api_key_override: str | None = None,
) -> str:
    """经工厂发起 LLM 对话（唯一入口），解密 Key + 记账 + 返回文本。

    :param model: 若为 None，使用 ModelConfig 中的默认模型。
    :param api_key_override: 用户自有 API Key（M9-8）。非空则用用户 Key（一律按百炼
        compatible-mode 处理，base_url 固定百炼地址），否则用 ModelConfig 系统 Key。
        默认 None → 行为与之前完全一致（回归安全）。
    """
    import os

    # 环境变量兜底的 provider（魔搭/智谱，M10 临时）：从 env 读 key，不依赖 ModelConfig 表。
    # 用户级 env 需用 Win32 注册表读取（_read_user_env），process 继承不到。
    env_key_providers = {
        Provider.MODELSCOPE: MODELSCOPE_ENV_KEY,
        Provider.ZHIPU: ZHIPU_ENV_KEY,
        Provider.SILICONFLOW: SILICONFLOW_ENV_KEY,
    }
    if provider in env_key_providers:
        env_key_name = env_key_providers[provider]
        api_key = _read_user_env(env_key_name) or os.environ.get(env_key_name, "")
        if not api_key:
            raise LLMConfigError(
                f"{provider.value} key 未配置（环境变量 {env_key_name}）",
                code="env_provider_no_key",
            )
        # model 参数必传（无 ModelConfig 默认）；base_url 用 PROVIDER_BASE_URLS
        if not model:
            raise LLMConfigError(
                f"{provider.value} provider 需显式传 model 参数",
                code="env_provider_no_model",
            )
        base_url = PROVIDER_BASE_URLS[provider]
        # 走调用循环（不读 ModelConfig、不查 db.api_key）
        return _dispatch_openai_chat(
            db=db,
            api_key=api_key,
            base_url=base_url,
            use_anthropic=False,
            model=model,
            messages=messages,
            node=node,
            task_id=task_id,
            provider=provider,
        )

    cfg = get_active_model_config(db, provider)
    model = model or cfg.model

    # M9-8：用户自有 Key 一律按百炼 DashScope 兼容接口处理（谁用谁付费）
    if api_key_override:
        api_key = api_key_override
        base_url = PROVIDER_BASE_URLS[Provider.BAILIAN]
        use_anthropic = False
    else:
        api_key = decrypt_secret(cfg.api_key_encrypted)
        # anthropic 无 base_url（走专用接口），用 .get 避免 KeyError
        base_url = PROVIDER_BASE_URLS.get(provider)
        use_anthropic = provider == Provider.ANTHROPIC

    return _dispatch_call(
        db=db,
        api_key=api_key,
        base_url=base_url,
        use_anthropic=use_anthropic,
        model=model,
        messages=messages,
        node=node,
        task_id=task_id,
        provider=provider,
    )


def _dispatch_call(
    *,
    db: Session,
    api_key: str,
    base_url: str | None,
    use_anthropic: bool,
    model: str,
    messages: list[dict],
    node: str | None,
    task_id: Any | None,
    provider: Provider,
) -> str:
    """统一 LLM 调用 dispatch：重试 + 客户端选择 + 记账。

    供 chat_completion 常规路径和 ModelScope 早退路径共用。
    """
    # 降级容错（ARCHITECTURE 6.4）：失败重试 2 次（指数退避）；配置错误不重试
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            if use_anthropic:
                client = _build_anthropic_client(api_key)
                resp = _anthropic_completion(client, model, messages)
            else:
                client = _build_openai_client(api_key, base_url)
                resp = _openai_completion(client, model, messages)
            break
        except LLMConfigError:
            raise
        except Exception as exc:  # 网络/超时/限流 → 重试
            if attempt < LLM_MAX_RETRIES:
                # 429 限流用更长退避（20s/40s），其余走常规指数退避（2s/4s）
                is_429 = "429" in str(exc) or "rate limit" in str(exc).lower()
                backoff = LLM_429_BACKOFF if is_429 else LLM_RETRY_BACKOFF
                time.sleep(backoff * (2**attempt))
            else:
                raise LLMError(
                    f"LLM 调用重试 {LLM_MAX_RETRIES} 次仍失败: {exc}", code="llm_failed"
                ) from exc

    input_tokens = resp.get("input_tokens", 0)
    output_tokens = resp.get("output_tokens", 0)
    latency_ms = resp.get("latency_ms", 0)
    text = resp.get("text", "")

    _record_call(
        db=db,
        provider=provider,
        model=model,
        node=node,
        task_id=task_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )
    return text


# 向后兼容别名（旧代码/测试引用）
_dispatch_openai_chat = _dispatch_call


def _openai_completion(client: Any, model: str, messages: list[dict]) -> dict:
    """OpenAI 兼容接口对话，返回 {text, input_tokens, output_tokens, latency_ms}。"""
    start = time.monotonic()
    resp = client.chat.completions.create(model=model, messages=messages)
    elapsed = int((time.monotonic() - start) * 1000)
    return {
        "text": resp.choices[0].message.content or "",
        "input_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "output_tokens": resp.usage.completion_tokens if resp.usage else 0,
        "latency_ms": elapsed,
    }


def _anthropic_completion(client: Any, model: str, messages: list[dict]) -> dict:
    """Anthropic 接口对话（消息结构转 system/user 分离）。"""
    start = time.monotonic()
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    user_msgs = [{"role": "user", "content": m["content"]} for m in messages if m["role"] == "user"]
    kwargs: dict[str, Any] = {"model": model, "max_tokens": 4096, "messages": user_msgs}
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    elapsed = int((time.monotonic() - start) * 1000)
    return {
        "text": "".join(b.text for b in resp.content if getattr(b, "type", "") == "text"),
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "latency_ms": elapsed,
    }
