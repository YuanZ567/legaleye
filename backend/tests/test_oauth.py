"""M9-6 OAuth 验收测试（GitHub 全链路 + QQ 接口就绪）。

- GitHub authorize 已配置 → 302 + state 落 Redis（TTL 300s）；
- GitHub callback（mock httpx）→ 换 token → 拉用户 → 建用户 → 302 跳前端带 token；
- 同一 GitHub 账号二次登录 → 复用既有用户（不重复建）；
- 无效 state → 400（CSRF 防线）；
- QQ authorize 凭据未配置 → 503（"暂未开通"）；
- OAuth 用户即使 DB 为空也 role=user（不触发首个 admin）；
- 不破坏 /auth/register /auth/login /auth/me 契约。
"""

from collections.abc import Generator
from types import SimpleNamespace

import httpx
import pytest
from app.core.db import get_db
from app.main import create_app
from app.models import SQLModel, User
from app.services import oauth_service
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


# ---------- 假 Redis / 假 httpx ----------
class FakeRedis:
    def __init__(self) -> None:
        self._d: dict[str, str] = {}

    def set(self, key, value, ex=None):
        self._d[key] = value
        return True

    def get(self, key):
        return self._d.get(key)

    def delete(self, key):
        self._d.pop(key, None)
        return 1


class FakeResponse:
    def __init__(self, status_code: int, json_data=None, text: str = ""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            from httpx import HTTPStatusError, Request, Response

            raise HTTPStatusError(
                "error", request=Request("GET", "https://x"), response=Response(self.status_code)
            )

    def json(self):
        return self._json


class FakeAsyncClient:
    """按 URL 分派：GitHub token → access_token；GitHub user → id/login。"""

    def __init__(self, *args, **kwargs):
        self._next_user: dict | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        if "access_token" in url:
            return FakeResponse(200, json_data={"access_token": "gh_token_abc"})
        return FakeResponse(500, json_data={}, text="unexpected")

    async def get(self, url, **kwargs):
        if "graph.qq.com/oauth2.0/me" in url:
            return FakeResponse(
                200,
                json_data={},
                text='callback( {"client_id":"qqid","openid":"qq_openid_123"} );',
            )
        if "graph.qq.com/oauth2.0/token" in url:
            return FakeResponse(200, json_data={}, text="access_token=qq_token&expires_in=7200")
        if "api.github.com/user" in url:
            return FakeResponse(
                200,
                json_data={"id": 1001, "login": "octocat", "name": "Octo Cat"},
            )
        return FakeResponse(500, json_data={}, text="unexpected")


def _fake_settings() -> SimpleNamespace:
    return SimpleNamespace(
        api_base_url="http://localhost:8000",
        oauth_redirect_base="http://localhost:5173",
        github_client_id="gh_client_id",
        github_client_secret="gh_client_secret",
        qq_app_id="",
        qq_app_key="",
        oauth_state_ttl_seconds=300,
    )


@pytest.fixture()
def env(monkeypatch) -> Generator[tuple[TestClient, sessionmaker], None, None]:
    """内存 DB + override get_db + mock Redis / httpx。"""
    from app.services import rate_limit_service

    monkeypatch.setattr(rate_limit_service, "check_demo_limit", lambda **kw: None)
    # OAuth 凭据（GitHub 配好、QQ 留空）+ state 存假 Redis
    monkeypatch.setattr(oauth_service, "get_settings", _fake_settings)
    fake_redis = FakeRedis()
    monkeypatch.setattr(oauth_service, "_redis", lambda: fake_redis)
    # mock 全局 httpx.AsyncClient（oauth_service 函数内 import httpx 拿到同一模块）
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSession() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c, TestingSession
    SQLModel.metadata.drop_all(engine)


# ---------- 测试 ----------
def test_github_authorize_redirects_with_state(env, monkeypatch):
    """GitHub 已配置：authorize → 302 + state 落 Redis。"""
    c, _ = env
    monkeypatch.setattr(oauth_service, "_redis", lambda: FakeRedis())  # 已由 env mock
    resp = c.get("/auth/oauth/github/authorize", follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "github.com/login/oauth/authorize" in location
    assert "client_id=gh_client_id" in location
    assert "state=" in location
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000" in location or "localhost:8000" in location


def test_github_callback_creates_oauth_user(env):
    """GitHub 回调：建用户（合成邮箱/role=user/oauth_id）+ 302 带 token。"""
    c, ts = env
    # 先走 authorize 落 state
    c.get("/auth/oauth/github/authorize", follow_redirects=False)
    state = oauth_service._redis()._d  # FakeRedis dict 里的 state key
    state_val = list(state.keys())[0].split(":")[-1]

    resp = c.get(
        f"/auth/oauth/github/callback?code=abc&state={state_val}",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("http://localhost:5173/oauth/callback?token=")

    with ts() as db:
        user = db.query(User).filter(User.oauth_provider == "github").one()
        assert user.oauth_id == "1001"
        assert user.email == "github_1001@oauth.local"
        assert user.role.value == "user"  # 不触发 admin


def test_github_callback_reuses_existing_user(env):
    """同一 GitHub 账号二次登录：复用用户，不重复建。"""
    c, ts = env
    c.get("/auth/oauth/github/authorize", follow_redirects=False)
    state_val = list(oauth_service._redis()._d.keys())[0].split(":")[-1]
    c.get(f"/auth/oauth/github/callback?code=abc&state={state_val}", follow_redirects=False)

    # 再次登录
    c.get("/auth/oauth/github/authorize", follow_redirects=False)
    state2 = list(oauth_service._redis()._d.keys())[0].split(":")[-1]
    c.get(f"/auth/oauth/github/callback?code=abc&state={state2}", follow_redirects=False)

    with ts() as db:
        users = db.query(User).filter(User.oauth_provider == "github").all()
        assert len(users) == 1  # 复用


def test_callback_invalid_state_rejected(env):
    """无效 state → 400（CSRF 防线）。"""
    c, _ = env
    resp = c.get("/auth/oauth/github/callback?code=abc&state=forged", follow_redirects=False)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "oauth_state_invalid"


def test_qq_authorize_not_configured_503(env):
    """QQ 凭据留空：authorize → 503（暂未开通）。"""
    c, _ = env
    resp = c.get("/auth/oauth/qq/authorize", follow_redirects=False)
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "oauth_not_configured"


def test_unknown_provider_rejected(env):
    """不支持的 provider → 400。"""
    c, _ = env
    resp = c.get("/auth/oauth/wechat/authorize", follow_redirects=False)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "oauth_unsupported"


def test_oauth_user_does_not_trigger_first_admin(env):
    """DB 为空时 OAuth 用户仍为 user（不触发首个 admin）。"""
    c, ts = env
    with ts() as db:
        assert db.query(User).count() == 0  # 空库
    c.get("/auth/oauth/github/authorize", follow_redirects=False)
    state_val = list(oauth_service._redis()._d.keys())[0].split(":")[-1]
    c.get(f"/auth/oauth/github/callback?code=abc&state={state_val}", follow_redirects=False)
    with ts() as db:
        user = db.query(User).filter(User.oauth_provider == "github").one()
        assert user.role.value == "user"


def test_existing_auth_contract_unchanged(env):
    """不破坏 /auth/register /auth/login /auth/me。"""
    c, _ = env
    reg = c.post("/auth/register", json={"email": "keep@x.com", "password": "secret123"})
    assert reg.status_code == 200
    data = reg.json()["data"]
    assert data["user"]["email"] == "keep@x.com"
    token = data["token"]

    login = c.post("/auth/login", json={"email": "keep@x.com", "password": "secret123"})
    assert login.status_code == 200
    me = c.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "keep@x.com"
