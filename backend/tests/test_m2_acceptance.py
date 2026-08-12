"""M2-6 收尾抽查：检索 API 有命中时的契约正确性（mock embedding）。

- 命中结果字段对齐 DATA_CONTRACT 4.10（clauseRef/statuteVersion/articleText/score，camelCase）；
- 排序按 score 降序；
- 无命中返回空（不编造）由 test_law_retrieval 已覆盖，此处补"有命中"路径。
"""

from collections.abc import Generator

import pytest
from app.core.db import get_db
from app.main import create_app
from app.models import SQLModel
from app.models.law_baseline import LawBaseline
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


def test_search_returns_hits_with_contract_fields(client: TestClient, monkeypatch):
    """有命中时返回契约字段且按 score 降序。"""
    import app.api.knowledge as knowledge_api
    from app.knowledge.retrieval import LawHit

    hits = [
        LawHit(
            clause_ref="第四十条",
            statute_version="laws-v1.0-20260812",
            article_text="向境外提供个人信息应当具备条件之一",
            score=0.80,
        ),
        LawHit(
            clause_ref="第二条",
            statute_version="laws-v1.0-20260812",
            article_text="境外处理境内自然人个人信息的活动也适用本法",
            score=0.65,
        ),
    ]
    monkeypatch.setattr(knowledge_api, "semantic_search", lambda **kw: hits)

    resp = client.post("/knowledge/laws/search", json={"query": "跨境提供条件"})
    assert resp.status_code == 200, resp.text
    results = resp.json()["data"]["results"]
    assert len(results) == 2
    # 契约字段（camelCase）
    assert results[0]["clauseRef"] == "第四十条"
    assert results[0]["statuteVersion"] == "laws-v1.0-20260812"
    assert results[0]["articleText"].startswith("向境外")
    assert results[0]["score"] == 0.80
    # 按 score 降序
    assert results[0]["score"] >= results[1]["score"]


def test_law_baseline_out_contract_fields(client: TestClient):
    """GET /knowledge/laws 返回 LawBaseline 契约字段（camelCase）。"""
    from datetime import date

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestingSession() as session:
        session.add(
            LawBaseline(
                statute="个人信息保护法",
                article_no="第一条",
                article_text="为了保护个人信息权益，制定本法。",
                version="laws-v1.0-20260812",
                effective_date=date(2021, 11, 1),
                source="官方公布文本",
            )
        )
        session.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSession() as session:
            yield session

    from app.core.db import get_db as _get_db

    app = create_app()
    app.dependency_overrides[_get_db] = override_get_db
    with TestClient(app) as c:
        resp = c.get("/knowledge/laws")
    assert resp.status_code == 200, resp.text
    row = resp.json()["data"][0]
    assert row["articleNo"] == "第一条"
    assert row["articleText"].startswith("为了保护")
    assert row["effectiveDate"] == "2021-11-01"
    assert row["version"] == "laws-v1.0-20260812"
    SQLModel.metadata.drop_all(engine)
