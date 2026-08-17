"""M9-7 管理员功能验收测试（任务删除 + 知识库添加法条）。

- 非 admin 调 DELETE /tasks → 403；admin → 200 且 findings/report 级联消失；
- 删除不存在任务 → 404；
- 非 admin 调 POST /knowledge/laws → 403；
- admin 添加法条成功 → 出现在列表 + 可被 search 检索（mock embedding）；
- 重复添加同 statute+article_no → 409。
"""

import uuid
from collections.abc import Generator

import pytest
from app.core.db import get_db
from app.core.enums import FindingLevel, FindingVerdict, ReviewDimension
from app.main import create_app
from app.models import ComplianceFinding, Report, ReviewTask, SQLModel
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _register(c: TestClient, email: str) -> dict:
    resp = c.post("/auth/register", json={"email": email, "password": "secret123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]  # {token, user}


@pytest.fixture()
def env(monkeypatch) -> Generator[tuple[TestClient, sessionmaker], None, None]:
    """内存 DB + override get_db + mock embedding provider（不真调百炼）。"""
    from app.llm import embeddings
    from app.services import rate_limit_service

    monkeypatch.setattr(rate_limit_service, "check_demo_limit", lambda **kw: None)

    class FakeProvider:
        def embed(self, texts):
            # 稳定向量（按文本哈希），供 search 断言可区分
            return [[float(ord(ch) % 9 + 1) for ch in t[:8].ljust(8, " ")] for t in texts]

    monkeypatch.setattr(embeddings, "get_embedding_provider", lambda: FakeProvider())

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite 默认关外键：启用之，以在测试环境验证 ondelete=CASCADE 级联删除
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


def _make_task_with_findings_and_report(
    TestingSession, *, user_id: uuid.UUID | None = None
) -> uuid.UUID:
    task_id = uuid.uuid4()
    with TestingSession() as db:
        db.add(ReviewTask(id=task_id, document_id=uuid.uuid4(), status="done", user_id=user_id))
        db.flush()
        db.add(
            ComplianceFinding(
                task_id=task_id,
                dimension=ReviewDimension.D1_COLLECTION,
                verdict=FindingVerdict.NON_COMPLIANT,
                level=FindingLevel.HIGH,
                clause_ref="第五条",
            )
        )
        db.add(
            Report(
                task_id=task_id,
                baseline_version="laws-v1.0-20260811",
                content_json={"findingCount": 1, "highRiskCount": 1},
                md_export="# demo",
            )
        )
        db.commit()
    return task_id


# ---------- 删除任务 ----------
def test_delete_task_requires_admin(env):
    """非 admin 调 DELETE /tasks → 403。"""
    c, ts = env
    _register(c, "admin@x.com")  # 首个 = admin
    normal = _register(c, "user@x.com")  # 普通用户
    task_id = _make_task_with_findings_and_report(ts)

    resp = c.delete(f"/tasks/{task_id}", headers={"Authorization": f"Bearer {normal['token']}"})
    assert resp.status_code == 403


def test_admin_delete_task_cascades(env):
    """admin 删除任务成功 → findings + report 级联消失。"""
    c, ts = env
    admin = _register(c, "admin@x.com")
    task_id = _make_task_with_findings_and_report(ts)

    resp = c.delete(f"/tasks/{task_id}", headers={"Authorization": f"Bearer {admin['token']}"})
    assert resp.status_code == 200

    with ts() as db:
        assert db.get(ReviewTask, task_id) is None
        # 级联：findings + report 均已删除
        assert db.query(ComplianceFinding).filter(ComplianceFinding.task_id == task_id).count() == 0
        assert db.query(Report).filter(Report.task_id == task_id).count() == 0


def test_delete_nonexistent_task_404(env):
    """删除不存在任务 → 404。"""
    c, ts = env
    admin = _register(c, "admin@x.com")
    resp = c.delete(f"/tasks/{uuid.uuid4()}", headers={"Authorization": f"Bearer {admin['token']}"})
    assert resp.status_code == 404


# ---------- 添加法条 ----------
def test_add_law_requires_admin(env):
    """非 admin 调 POST /knowledge/laws → 403。"""
    c, ts = env
    _register(c, "admin@x.com")
    normal = _register(c, "user@x.com")
    resp = c.post(
        "/knowledge/laws",
        headers={"Authorization": f"Bearer {normal['token']}"},
        json={
            "statute": "个人信息保护法",
            "articleNo": "第 100 条",
            "articleText": "测试条款，长度至少十个字以上满足校验要求。",
            "effectiveDate": "2026-01-01",
            "source": "测试",
        },
    )
    assert resp.status_code == 403


def test_admin_add_law_success_and_searchable(env, monkeypatch):
    """admin 添加法条成功 → 出现在列表 + embedding 已写入（可被检索）。"""
    c, ts = env
    admin = _register(c, "admin@x.com")
    payload = {
        "statute": "个人信息保护法",
        "articleNo": "第 100 条",
        "articleText": "跨境传输个人信息应当依法取得单独同意并评估风险。",
        "effectiveDate": "2026-01-01",
        "source": "admin 手动录入",
    }
    resp = c.post(
        "/knowledge/laws",
        headers={"Authorization": f"Bearer {admin['token']}"},
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["articleNo"] == "第 100 条"
    assert data["version"] == "laws-v1.0-20260811"  # 默认基线版本

    # 出现在列表
    laws = c.get("/knowledge/laws").json()["data"]
    assert any(item["articleNo"] == "第 100 条" for item in laws)

    # embedding 已写入（pgvector 真实验证需 PG；SQLite 只验证向量非空 + 检索被调用）
    from app.models.law_baseline import LawBaseline
    from sqlalchemy import select

    with ts() as db:
        law = db.scalar(select(LawBaseline).where(LawBaseline.article_no == "第 100 条"))
        assert law is not None
        assert law.embedding is not None and len(law.embedding) > 0

    # 检索端点可命中（mock semantic_search 返回该条款，SQLite 无法跑 pgvector 排序）
    import app.api.knowledge as knowledge_api
    from app.knowledge.retrieval import LawHit

    monkeypatch.setattr(
        knowledge_api,
        "semantic_search",
        lambda **kw: [
            LawHit(
                clause_ref="第 100 条",
                statute_version="laws-v1.0-20260811",
                article_text=payload["articleText"],
                score=0.95,
            )
        ],
    )
    hits = c.post("/knowledge/laws/search", json={"query": "跨境传输单独同意"}).json()["data"][
        "results"
    ]
    assert len(hits) == 1
    assert hits[0]["clauseRef"] == "第 100 条"


def test_admin_add_law_duplicate_409(env):
    """重复添加同 statute+article_no → 409。"""
    c, ts = env
    admin = _register(c, "admin@x.com")
    payload = {
        "statute": "个人信息保护法",
        "articleNo": "第 101 条",
        "articleText": "重复条款用于测试去重逻辑是否生效。",
        "effectiveDate": "2026-01-01",
        "source": "测试",
    }
    first = c.post(
        "/knowledge/laws",
        headers={"Authorization": f"Bearer {admin['token']}"},
        json=payload,
    )
    assert first.status_code == 200
    second = c.post(
        "/knowledge/laws",
        headers={"Authorization": f"Bearer {admin['token']}"},
        json=payload,
    )
    assert second.status_code == 409
