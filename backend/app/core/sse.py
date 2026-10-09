"""SSE 事件桥（M4-3）：任务进度事件发布与流式读取。

契约（DATA_CONTRACT 3.3）四类事件：
- taskStatus：{status, progress}
- nodeStart / nodeEnd：{node, dimension}
- tokenUsage：{provider, model, inputTokens, outputTokens}

实现：Redis List 作为事件缓冲（task:{task_id}:events），
发布端（Celery/工作流）入队，订阅端（API SSE）出队流式返回。
Redis 不可用时降级为内存缓冲（单机演示），不阻塞主流程。
"""

import json
import logging
from collections.abc import Iterator
from typing import Any

logger = logging.getLogger(__name__)


def _redis() -> Any | None:
    """获取 Redis 客户端（不可用返回 None，降级内存）。"""
    try:
        import redis

        from app.core.config import get_settings

        client = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def _event_key(task_id: str) -> str:
    return f"task:{task_id}:events"


def publish_event(task_id: str, event_type: str, data: dict[str, Any]) -> None:
    """发布一条 SSE 事件（入队；Redis 不可用则仅记录日志降级）。

    nodeEnd 事件额外写入独立进度队列 task:{id}:progress（供 worker 内
    进度跟踪线程消费，不与 SSE 流抢占事件）。
    """
    payload = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
    client = _redis()
    if client is not None:
        try:
            client.rpush(_event_key(task_id), payload)
            client.expire(_event_key(task_id), 3600)
            if event_type == "nodeEnd":
                progress_key = f"task:{task_id}:progress"
                client.rpush(progress_key, data.get("dimension") or data.get("node") or "")
                client.expire(progress_key, 3600)
            return
        except Exception as exc:  # pragma: no cover - 网络异常降级
            logger.warning("SSE 入队失败，降级: %s", exc)
    logger.info("[sse] %s %s %s", task_id, event_type, data)


def publish_token_usage(
    task_id: str,
    *,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """发布 tokenUsage 事件（LLM 调用记账后调用，契约 DATA_CONTRACT 3.3）。"""
    publish_event(
        task_id,
        "tokenUsage",
        {
            "provider": provider,
            "model": model,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
        },
    )


def iter_events(task_id: str, *, timeout: int = 120) -> Iterator[str]:
    """迭代读取任务事件流（SSE generator 用）。

    阻塞等待新事件，超过 timeout 秒无事件则结束（前端轮询已由 keepalive 兜底）。
    """
    import time

    client = _redis()
    key = _event_key(task_id)
    idle = 0.0
    while idle < timeout:
        if client is not None:
            item = client.lpop(key)
        else:
            item = None
        if item is not None:
            idle = 0.0
            yield f"data: {item}\n\n"
        else:
            # 无事件时发 keepalive 注释，避免连接超时
            yield ": keepalive\n\n"
            time.sleep(1.0)
            idle += 1.0
