"""M8-1 验收测试：注册/登录/JWT/双角色。

- 首个注册用户为 admin，后续为 user；
- 注册/登录返回 {token, user}（camelCase）；
- /auth/me 用 Bearer token 返回当前用户；
- 重复注册 → 400；未登录访问 /auth/me → 401。
"""

from collections.abc import Generator

import pytest
from app.core.db import get_db
from app.main import create_app
from app.models import SQLModel
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
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
        yield c
    SQLModel.metadata.drop_all(engine)


def _register(client: TestClient, email: str, password: str = "secret123"):
    return client.post("/auth/register", json={"email": email, "password": password})


def test_first_user_is_admin(client: TestClient):
    """首个注册用户 role=admin。"""
    resp = _register(client, "admin@example.com")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["user"]["role"] == "admin"
    assert data["token"]


def test_second_user_is_user(client: TestClient):
    """后续注册用户 role=user。"""
    _register(client, "admin@example.com")
    resp = _register(client, "user@example.com")
    assert resp.status_code == 200
    assert resp.json()["data"]["user"]["role"] == "user"


def test_login_returns_token(client: TestClient):
    """登录返回 token + user（camelCase createdAt）。"""
    _register(client, "a@example.com")
    resp = client.post("/auth/login", json={"email": "a@example.com", "password": "secret123"})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["token"]
    assert data["user"]["email"] == "a@example.com"
    assert "createdAt" in data["user"]


def test_login_wrong_password_400(client: TestClient):
    """错误密码 → 400 invalid_credentials。"""
    _register(client, "a@example.com")
    resp = client.post("/auth/login", json={"email": "a@example.com", "password": "wrongpass"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_credentials"


def test_me_with_token(client: TestClient):
    """/auth/me 用 Bearer token 返回当前用户。"""
    token = _register(client, "me@example.com").json()["data"]["token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["email"] == "me@example.com"


def test_me_unauthorized_401(client: TestClient):
    """未登录访问 /auth/me → 401。"""
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_duplicate_email_400(client: TestClient):
    """重复邮箱注册 → 400 email_taken。"""
    _register(client, "dup@example.com")
    resp = _register(client, "dup@example.com")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "email_taken"
