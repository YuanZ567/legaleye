"""M8-5 收尾验收：认证→模型配置→任务链路（admin 端到端）。

- 首个注册用户为 admin；
- admin 保存模型配置（apiKeyTail 脱敏）；
- 创建任务可被 GET /tasks 列出（多用户隔离由 user_id 保证，前端隐藏）。
"""

import uuid
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
def client(monkeypatch) -> Generator[TestClient, None, None]:
    # 避免 demo 限流干扰
    from app.services import rate_limit_service

    monkeypatch.setattr(rate_limit_service, "check_demo_limit", lambda **kw: None)

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


def test_admin_flow_register_model_task(client: TestClient):
    """admin 端到端：注册 → 保存模型 → 创建任务 → 列表可见。"""
    import app.api.tasks as tasks_api

    # 1) 注册首个用户 → admin
    token = client.post(
        "/auth/register", json={"email": "admin@x.com", "password": "secret123"}
    ).json()["data"]["token"]
    assert token

    # 2) admin 保存模型配置（apiKeyTail 脱敏）
    resp = client.post(
        "/models",
        headers={"Authorization": f"Bearer {token}"},
        json={"provider": "bailian", "apiKey": "sk-test-xxxx-5678", "model": "qwen3.7-flash"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["apiKeyTail"] == "5678"
    assert "sk-test" not in resp.text  # 无明文 Key

    # 3) 创建任务（mock dispatch 避免真实 broker）
    original_dispatch = tasks_api.dispatch_task
    tasks_api.dispatch_task = lambda task_id, document_id: None
    try:
        resp = client.post("/tasks", json={"documentIds": [str(uuid.uuid4())]})
    finally:
        tasks_api.dispatch_task = original_dispatch
    assert resp.status_code == 200, resp.text

    # 4) 任务列表可见
    listed = client.get("/tasks").json()["data"]
    assert len(listed) >= 1
    assert all(t["status"] == "queued" for t in listed)
