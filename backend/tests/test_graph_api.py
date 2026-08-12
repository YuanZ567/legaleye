"""M3-5 验收测试：图谱 API（GET /documents/{id}/graph）。

用内存 SQLite 构造一个含跨境条款的 Document，验证：
- 返回 GraphPayload 契约字段（entities/edges/riskPaths/suggestions）；
- R1 风险路径识别（含 crossBorder）；
- 文档不存在返回 404。
"""

import uuid
from collections.abc import Generator

import pytest
from app.core.db import get_db
from app.core.enums import DocType
from app.main import create_app
from app.models import Document, SQLModel
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _make_document(raw_text: str) -> Document:
    return Document(
        filename="policy.pdf",
        doc_type=DocType.PRIVACY_POLICY,
        raw_text=raw_text,
        text_preview=raw_text[:100],
        sensitive_mode=False,
    )


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


def test_graph_api_returns_payload():
    """GET /documents/{id}/graph 返回 GraphPayload 契约（含 R1 风险路径）。"""
    raw = (
        "我们（个人信息处理者）为提供电商服务，收集您的手机号和账号信息。"
        "我们委托云服务商存储个人信息。"
        "我们向境外子公司跨境提供用户手机号，用于数据分析。"
    )
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSession() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestingSession() as session:
        doc = _make_document(raw)
        session.add(doc)
        session.commit()
        doc_id = doc.id

    with TestClient(app) as c:
        resp = c.get(f"/documents/{doc_id}/graph")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    # 契约字段存在
    assert "entities" in data and "edges" in data
    assert "riskPaths" in data and "suggestions" in data
    # 存在跨境风险路径
    assert data["riskPaths"] or any(e.get("type") == "crossBorder" for e in data["edges"])
    # 实体含 dataCategory（手机号）
    assert any(e["role"] == "dataCategory" for e in data["entities"])


def test_graph_api_404(client: TestClient):
    """文档不存在 → 404。"""
    missing_id = uuid.uuid4()
    resp = client.get(f"/documents/{missing_id}/graph")
    assert resp.status_code == 404
