"""M9-8 用户级 API Key 验收测试（谁用谁付费）。

- 设置 Key → apiKeyTail 尾号 4 位、明文不回显；
- 清除 Key → 字段置空；
- 未登录调 PUT /users/me/api-key → 401；
- 有 Key 用户创建任务 → 不限流（check_demo_limit 未调用）；
- 无 Key 用户创建任务 → 限流计数（check_demo_limit 被调用）；
- worker：有 Key 用户 → api_key_override 透传；无 Key → 不传。
"""

import uuid
from collections.abc import Generator
from unittest import mock

import pytest
from app.core.db import get_db
from app.main import create_app
from app.models import Document, ReviewTask, SQLModel, User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _register(c: TestClient, email: str) -> dict:
    resp = c.post("/auth/register", json={"email": email, "password": "secret123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.fixture()
def env(monkeypatch) -> Generator[tuple[TestClient, sessionmaker], None, None]:
    """内存 DB + override get_db + mock rate_limit（spy 记录调用）。"""
    from app.services import rate_limit_service

    spy = mock.MagicMock()
    monkeypatch.setattr(rate_limit_service, "check_demo_limit", spy)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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


def _make_doc(TestingSession) -> uuid.UUID:
    with TestingSession() as db:
        doc = Document(filename="demo.pdf", doc_type="privacyPolicy", char_count=10, raw_text="x")
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc.id


def test_set_api_key_tail_only(env):
    """设置 Key → apiKeyTail 尾号 4 位、明文不回显。"""
    c, ts = env
    data = _register(c, "a@x.com")
    resp = c.put(
        "/users/me/api-key",
        headers={"Authorization": f"Bearer {data['token']}"},
        json={"apiKey": "sk-abcdef123456"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["apiKeyTail"] == "****3456"
    body = resp.text
    assert "sk-abcdef123456" not in body  # 明文绝不出 API

    # /auth/me 也带尾号
    me = c.get("/auth/me", headers={"Authorization": f"Bearer {data['token']}"}).json()["data"]
    assert me["apiKeyTail"] == "****3456"

    # 库中只存密文 + 尾号
    with ts() as db:
        user = db.query(User).filter(User.email == "a@x.com").one()
        assert user.api_key_encrypted and "sk-abcdef123456" not in user.api_key_encrypted
        assert user.api_key_tail == "3456"


def test_clear_api_key(env):
    """清除 Key → 字段置空。"""
    c, ts = env
    data = _register(c, "b@x.com")
    c.put(
        "/users/me/api-key",
        headers={"Authorization": f"Bearer {data['token']}"},
        json={"apiKey": "sk-1234567890"},
    )
    resp = c.delete("/users/me/api-key", headers={"Authorization": f"Bearer {data['token']}"})
    assert resp.status_code == 200
    with ts() as db:
        user = db.query(User).filter(User.email == "b@x.com").one()
        assert user.api_key_encrypted is None
        assert user.api_key_tail is None


def test_set_key_requires_auth(env):
    """未登录调 PUT → 401。"""
    c, _ = env
    resp = c.put("/users/me/api-key", json={"apiKey": "sk-123"})
    assert resp.status_code == 401


def test_has_key_skips_rate_limit(env):
    """有 Key 用户创建任务 → check_demo_limit 未调用（无限次）。"""
    c, ts = env
    from app.services import rate_limit_service

    data = _register(c, "paid@x.com")
    c.put(
        "/users/me/api-key",
        headers={"Authorization": f"Bearer {data['token']}"},
        json={"apiKey": "sk-abc123456789"},
    )
    doc_id = _make_doc(ts)

    import app.api.tasks as tasks_api

    original = tasks_api.dispatch_task
    tasks_api.dispatch_task = lambda **kw: None
    try:
        resp = c.post(
            "/tasks",
            headers={"Authorization": f"Bearer {data['token']}"},
            json={"documentIds": [str(doc_id)]},
        )
    finally:
        tasks_api.dispatch_task = original
    assert resp.status_code == 200
    assert rate_limit_service.check_demo_limit.call_count == 0  # 未限流


def test_no_key_rate_limited(env):
    """无 Key 用户创建任务 → check_demo_limit 被调用（按 user_id 计数）。"""
    c, ts = env
    from app.services import rate_limit_service

    data = _register(c, "demo@x.com")
    doc_id = _make_doc(ts)

    import app.api.tasks as tasks_api

    original = tasks_api.dispatch_task
    tasks_api.dispatch_task = lambda **kw: None
    try:
        resp = c.post(
            "/tasks",
            headers={"Authorization": f"Bearer {data['token']}"},
            json={"documentIds": [str(doc_id)]},
        )
    finally:
        tasks_api.dispatch_task = original
    assert resp.status_code == 200
    assert rate_limit_service.check_demo_limit.call_count == 1


def test_worker_passes_override_when_has_key(env, monkeypatch):
    """worker：有 Key 用户 → api_key_override 透传；无 Key → 不传。"""
    from app.tasks import review_task as rt

    captured: dict = {}

    class FakeGraph:
        async def ainvoke(self, state):
            captured["override"] = state.get("api_key_override")
            return {"findings": []}

    monkeypatch.setattr(rt, "publish_event", lambda *a, **k: None)
    monkeypatch.setattr(rt, "generate_report", lambda **kw: None)
    monkeypatch.setattr(rt, "build_workflow", lambda: FakeGraph())

    _, ts = env  # 复用 env fixture 的内存 DB
    doc_id = uuid.uuid4()
    task_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    # 有 Key 用户
    from app.core.security import encrypt_secret

    with ts() as db:
        db.add(
            User(
                id=owner_id,
                email="worker@x.com",
                password_hash="x",
                role="user",
                api_key_encrypted=encrypt_secret("sk-worker-secret"),
                api_key_tail="cret",
            )
        )
        db.add(ReviewTask(id=task_id, document_id=doc_id, status="queued", user_id=owner_id))
        db.add(
            Document(id=doc_id, filename="x", doc_type="privacyPolicy", char_count=1, raw_text="t")
        )
        db.commit()

    monkeypatch.setattr(rt, "SessionLocal", lambda: _session_from(ts))
    rt._run_workflow(task_id=task_id, document_id=doc_id)
    assert captured["override"] == "sk-worker-secret"  # 有 Key → 透传明文

    # 无 Key 用户 → 不传
    doc2, task2, owner2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    with ts() as db:
        db.add(User(id=owner2, email="nokey@x.com", password_hash="x", role="user"))
        db.add(ReviewTask(id=task2, document_id=doc2, status="queued", user_id=owner2))
        db.add(
            Document(id=doc2, filename="y", doc_type="privacyPolicy", char_count=1, raw_text="s")
        )
        db.commit()
    rt._run_workflow(task_id=task2, document_id=doc2)
    assert captured["override"] is None  # 无 Key → 不传


def _session_from(sessionmaker_):
    """生成上下文管理器风格的 Session（供 SessionLocal 使用）。"""
    from contextlib import contextmanager

    @contextmanager
    def _cm():
        with sessionmaker_() as session:
            yield session

    return _cm()
