"""M4-5 验收测试：任务 API（创建/详情/SSE 四类事件）。

- POST /tasks 创建任务（返回 taskId，分发 Celery）;
- GET /tasks/{id} 详情（状态/progress）;
- SSE 事件：taskStatus/nodeStart/nodeEnd/tokenUsage 可发布并被迭代读取;
- 任务不存在返回 404。
"""

import uuid
from collections.abc import Generator

import pytest
from app.core.db import get_db
from app.core.sse import publish_event
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


def test_create_task_returns_id(client: TestClient, monkeypatch):
    """POST /tasks 创建任务返回 taskId，并分发 Celery。"""
    import app.api.tasks as tasks_api

    dispatched = []

    def fake_dispatch(task_id, document_id):  # noqa: ARG001
        dispatched.append(task_id)

    monkeypatch.setattr(tasks_api, "dispatch_task", fake_dispatch)

    doc_id = uuid.uuid4()
    resp = client.post("/tasks", json={"documentIds": [str(doc_id)], "taskType": "compliance"})
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["taskId"]
    assert task_id
    assert len(dispatched) == 1


def test_create_task_empty_docs_400(client: TestClient):
    """空 documentIds → 400。"""
    resp = client.post("/tasks", json={"documentIds": [], "taskType": "compliance"})
    assert resp.status_code == 400


def test_get_task_detail(client: TestClient, monkeypatch):
    """GET /tasks/{id} 返回任务状态。"""
    import app.api.tasks as tasks_api

    monkeypatch.setattr(tasks_api, "dispatch_task", lambda task_id, document_id: None)

    doc_id = uuid.uuid4()
    create_resp = client.post("/tasks", json={"documentIds": [str(doc_id)]})
    task_id = create_resp.json()["taskId"]

    resp = client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "queued"


def test_get_task_404(client: TestClient):
    """任务不存在 → 404。"""
    resp = client.get(f"/tasks/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_sse_four_event_types_publish_and_read(monkeypatch):
    """taskStatus/nodeStart/nodeEnd/tokenUsage 四类事件可发布并被 SSE 迭代读取。"""
    import app.core.sse as sse

    # fake Redis：内存 list，使 publish 与 iter 共享同一缓冲
    class FakeRedis:
        def __init__(self) -> None:
            self.store: dict[str, list] = {}

        def rpush(self, key, value):
            self.store.setdefault(key, []).append(value)

        def lpop(self, key):
            if self.store.get(key):
                return self.store[key].pop(0)
            return None

        def expire(self, key, ttl):  # noqa: ARG002
            return None

    fake = FakeRedis()
    monkeypatch.setattr(sse, "_redis", lambda: fake)

    task_id = "task-sse-1"
    publish_event(task_id, "taskStatus", {"status": "running", "progress": 10})
    publish_event(task_id, "nodeStart", {"node": "agent", "dimension": "d1"})
    publish_event(task_id, "nodeEnd", {"node": "agent", "dimension": "d1"})
    publish_event(task_id, "tokenUsage", {"provider": "bailian", "model": "qwen-plus"})

    events = list(sse.iter_events(task_id, timeout=1))
    data = [e for e in events if e.startswith("data:")]
    assert len(data) >= 4  # 至少四类事件
    joined = "\n".join(data)
    assert "taskStatus" in joined
    assert "nodeStart" in joined
    assert "nodeEnd" in joined
    assert "tokenUsage" in joined
