"""M8-3 验收测试：模型配置（四 provider 保存/激活/测试）。

- admin 鉴权：非 admin 访问 /models → 403；
- 保存：apiKeyTail 脱敏尾号 4 位，响应绝不含明文 Key；
- 激活：事务停用旧 active、启用目标；
- test：mock provider 成功/失败（无效 Key 保存前拦截）。
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


def _register_admin(client: TestClient, email="admin@x.com", password="secret123") -> str:
    """注册 admin（首个用户）并返回 token。"""
    return client.post("/auth/register", json={"email": email, "password": password}).json()[
        "data"
    ]["token"]


def _register_user(client: TestClient, email="user@x.com") -> str:
    """注册普通用户（需先已注册 admin）并返回 token。"""
    return client.post("/auth/register", json={"email": email, "password": "secret123"}).json()[
        "data"
    ]["token"]


def test_models_require_admin(client: TestClient):
    """非 admin 访问 /models → 403。"""
    _register_admin(client)
    user_token = _register_user(client)
    resp = client.get("/models", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403


def test_create_model_masked_tail(client: TestClient):
    """保存模型：apiKeyTail 尾号 4 位，响应不含明文 Key。"""
    admin_token = _register_admin(client)
    resp = client.post(
        "/models",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"provider": "bailian", "apiKey": "sk-test-abcdef1234", "model": "qwen3.7-flash"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["apiKeyTail"] == "1234"  # 尾号 4 位
    assert data["isActive"] is True  # 首个自动激活
    assert "sk-test" not in resp.text  # 不含明文 Key


def test_activate_switches_transactional(client: TestClient):
    """激活切换：停用旧 active、启用目标（事务保证）。"""
    admin_token = _register_admin(client)
    # 建两个模型
    m1 = client.post(
        "/models",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"provider": "bailian", "apiKey": "sk-1111", "model": "qwen-a"},
    ).json()["data"]
    m2 = client.post(
        "/models",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"provider": "deepseek", "apiKey": "sk-2222", "model": "deepseek-v3"},
    ).json()["data"]
    # m1 active，m2 inactive
    assert m1["isActive"] is True
    assert m2["isActive"] is False

    # 激活 m2 → m1 停用
    resp = client.put(
        f"/models/{m2['id']}/activate", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["isActive"] is True
    # 查列表确认 m1 停用
    listed = client.get("/models", headers={"Authorization": f"Bearer {admin_token}"}).json()[
        "data"
    ]
    active = [m for m in listed if m["isActive"]]
    assert len(active) == 1 and active[0]["id"] == m2["id"]


def test_test_model_success(client: TestClient, monkeypatch):
    """test：mock provider 成功 → ok:true。"""
    from app.api import models as models_api

    monkeypatch.setattr(models_api, "test_model", lambda **kw: {"ok": True})
    admin_token = _register_admin(client)
    resp = client.post(
        "/models/test",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"provider": "bailian", "apiKey": "sk-good-key", "model": "qwen3.7-flash"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["ok"] is True


def test_test_model_invalid_key(client: TestClient, monkeypatch):
    """test：无效 Key → 拦截（保存前）。"""
    from app.api import models as models_api
    from app.core.exceptions import ValidationError

    def fake_test(**kw):
        raise ValidationError("模型连接失败：无效 Key", code="model_test_failed")

    monkeypatch.setattr(models_api, "test_model", fake_test)
    admin_token = _register_admin(client)
    resp = client.post(
        "/models/test",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"provider": "bailian", "apiKey": "sk-invalid", "model": "qwen3.7-flash"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "model_test_failed"
