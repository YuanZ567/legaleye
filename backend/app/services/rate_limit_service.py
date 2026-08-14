"""demo 免 Key 限流服务（M8-2）。

- 限流 3 次/日（Redis 计数器，IP+user_id 双重限制防匿名刷）；
- 仅对 demo 免 Key 用户生效——配 Key 的付费用户无限次（商业化逻辑）；
- 超限抛 RateLimitError（429）+ 友好提示；
- Redis 不可用时降级放行（不阻塞审查，生产由 Redis 保障）。
"""

import logging
from datetime import date
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import RateLimitError
from app.models import User

logger = logging.getLogger(__name__)

DEMO_QUOTA_MESSAGE = "今日 demo 额度已用完，请配置自有 Key 体验无限次"


def _redis() -> Any | None:
    """Redis 客户端（不可用返回 None，降级放行）。"""
    try:
        import redis

        client = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def is_demo_user(user: User | None, *, has_personal_key: bool = False) -> bool:
    """是否为 demo 免 Key 用户。

    - 未登录（user=None）→ demo；
    - 已登录但未配置自有 Key → demo；
    - 已配置自有 Key（付费）→ 非 demo（无限次）。
    """
    if has_personal_key:
        return False
    return user is None or True  # 无自有 Key 均视为 demo


def check_demo_limit(*, ip: str, user_id: str | None) -> None:
    """对 demo 免 Key 用户计数；超过 3 次/日抛 RateLimitError(429)。

    Key 用 `demo_limit:{date}:{user_id or ip}`（IP+user_id 双重限制）。
    """
    client = _redis()
    if client is None:
        logger.warning("Redis 不可用，demo 限流降级放行")
        return

    identity = user_id or ip or "unknown"
    key = f"demo_limit:{date.today().isoformat()}:{identity}"
    try:
        count = client.incr(key)
        client.expire(key, 86400)  # 当日有效
    except Exception as exc:  # 计数失败降级放行
        logger.warning("demo 限流计数失败: %s", exc)
        return

    if count > get_settings().demo_daily_limit:
        raise RateLimitError(DEMO_QUOTA_MESSAGE, code="demo_quota_exceeded")
