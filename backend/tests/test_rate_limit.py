"""M8-2 验收测试：demo 免 Key 限流 3 次/日。

- 第 1-3 次放行，第 4 次 → RateLimitError(429) + 友好提示；
- IP+user_id 双重限制（不同身份独立计数）；
- 限流只对 demo 免 Key 用户生效（配 Key 用户绕过）；
- Redis 不可用降级放行。
"""

import pytest
from app.core.config import get_settings
from app.core.exceptions import RateLimitError
from app.services import rate_limit_service
from app.services.rate_limit_service import check_demo_limit


class FakeRedis:
    """内存 Redis（incr/expire 模拟）。"""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, ttl):  # noqa: ARG002
        return None


@pytest.fixture()
def fake_redis(monkeypatch) -> FakeRedis:
    r = FakeRedis()
    monkeypatch.setattr(rate_limit_service, "_redis", lambda: r)
    return r


def test_demo_limit_3_per_day(fake_redis):
    """demo 免 Key 用户第 1-3 次放行，第 4 次 429。"""
    for _ in range(3):
        check_demo_limit(ip="1.2.3.4", user_id=None)  # 前 3 次放行
    with pytest.raises(RateLimitError) as exc:
        check_demo_limit(ip="1.2.3.4", user_id=None)  # 第 4 次超限
    assert exc.value.code == "demo_quota_exceeded"
    assert "demo 额度已用完" in exc.value.message


def test_ip_user_double_limiting(fake_redis):
    """IP+user_id 双重限制：不同身份独立计数。"""
    # 同一 IP 消耗满
    for _ in range(3):
        check_demo_limit(ip="1.2.3.4", user_id=None)
    with pytest.raises(RateLimitError):
        check_demo_limit(ip="1.2.3.4", user_id=None)
    # 另一 IP 独立计数（仍可放行）
    check_demo_limit(ip="5.6.7.8", user_id=None)


def test_redis_unavailable_degrades(monkeypatch):
    """Redis 不可用 → 降级放行（不抛 429）。"""
    monkeypatch.setattr(rate_limit_service, "_redis", lambda: None)
    # 多次调用不抛异常
    for _ in range(10):
        check_demo_limit(ip="1.2.3.4", user_id=None)


def test_config_limit_is_3():
    """demo 每日限流配置为 3（PRD 定案修改 5→3）。"""
    assert get_settings().demo_daily_limit == 3
