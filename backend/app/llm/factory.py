"""LLM 工厂（M4-1）：四 provider 路由 + Fernet 解密 + LLMCallRecord 记账。

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
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Provider
from app.core.exceptions import LLMError
from app.core.security import decrypt_secret
from app.models.model_config import LLMCallRecord, ModelConfig

logger = logging.getLogger(__name__)

# OpenAI 兼容接口的 base_url 路由（对齐架构 6.2）
PROVIDER_BASE_URLS: dict[Provider, str] = {
    Provider.BAILIAN: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    Provider.DEEPSEEK: "https://api.deepseek.com/v1",
    Provider.OPENAI: "https://api.openai.com/v1",
}


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
    """构造 OpenAI 兼容 client（bailian/deepseek/openai 共用）。"""
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=base_url)


def _build_anthropic_client(api_key: str) -> Any:
    """构造 Anthropic client。"""
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


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
    """写 LLMCallRecord 记账（L3）。"""
    db.add(
        LLMCallRecord(
            task_id=task_id,
            node=node,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_est=0.0,  # 成本估算在 M4 后续按 provider 单价补充
            latency_ms=latency_ms,
        )
    )
    db.commit()


def chat_completion(
    *,
    db: Session,
    provider: Provider,
    model: str | None,
    messages: list[dict],
    node: str | None = None,
    task_id: Any | None = None,
) -> str:
    """经工厂发起 LLM 对话（唯一入口），解密 Key + 记账 + 返回文本。

    :param model: 若为 None，使用 ModelConfig 中的默认模型。
    """
    cfg = get_active_model_config(db, provider)
    api_key = decrypt_secret(cfg.api_key_encrypted)
    model = model or cfg.model

    client = None
    if provider == Provider.ANTHROPIC:
        client = _build_anthropic_client(api_key)
        resp = _anthropic_completion(client, model, messages)
    else:
        client = _build_openai_client(api_key, PROVIDER_BASE_URLS[provider])
        resp = _openai_completion(client, model, messages)

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
