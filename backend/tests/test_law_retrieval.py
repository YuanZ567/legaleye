"""M2-5 验收测试：语义检索（mock embedding）。

单测用 mock embedding provider（CI 纪律：真实百炼集成 M4 统一接入）：
- `embed_law_baseline` 用 provider 为待回填条款生成向量；
- `semantic_search` 无命中返回空（不编造）；
- API `POST /knowledge/laws/search` 无命中返回 `{results: []}`。

注：pgvector 余弦排序的 Top-5 真实验证需 Postgres，见脚本/集成验证。
"""

from collections.abc import Generator
from datetime import date

import pytest
from app.core.db import get_db
from app.knowledge.retrieval import embed_law_baseline, semantic_search
from app.main import create_app
from app.models import SQLModel
from app.models.law_baseline import LawBaseline
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class MockEmbedding:
    """mock embedding：每个文本返回稳定的 4 维向量（embedding_dimension 用 4 验证逻辑）。"""

    def embed(self, texts: list[str]) -> list[list[float]]:
        # 用文本长度/哈希产生可区分向量，便于断言 provider 被调用
        return [[float(ord(ch) % 10 + 1) for ch in text[:4].ljust(4, " ")] for text in texts]


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestingSession() as session:
        yield session
    SQLModel.metadata.drop_all(engine)


def _law(text: str) -> LawBaseline:
    return LawBaseline(
        statute="个人信息保护法",
        article_no="第十三条",
        article_text=text,
        version="laws-v1.0-20260812",
        effective_date=date(2021, 11, 1),
        source="官方公布文本",
    )


def test_embed_law_baseline_calls_provider(db: Session):
    """embed_law_baseline 为 embedding 为 NULL 的条款调用 provider 并回填。"""
    db.add(_law("处理个人信息应当取得同意。"))
    db.commit()
    provider = MockEmbedding()
    filled = embed_law_baseline(db=db, provider=provider)
    assert filled == 1
    row = db.scalar(select(LawBaseline))
    assert row.embedding is not None and len(row.embedding) == 4


def test_semantic_search_no_hit_returns_empty(db: Session):
    """无 embedding 数据（SQLite 下向量全 NULL）→ 检索返回空，不编造。"""
    db.add(_law("处理个人信息应当取得同意。"))
    db.commit()
    hits = semantic_search(db=db, query="跨境提供个人信息的条件", provider=MockEmbedding())
    assert hits == []


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


def test_api_search_no_hit_returns_empty_results(client: TestClient, monkeypatch):
    """API：检索无命中返回 {results: []}（不编造），HTTP 200。"""
    import app.api.knowledge as knowledge_api

    # mock semantic_search 直接返回空（SQLite 无法跑 pgvector 排序）
    monkeypatch.setattr(knowledge_api, "semantic_search", lambda **kw: [])

    resp = client.post("/knowledge/laws/search", json={"query": "不存在的法条"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["results"] == []


def test_api_get_laws_empty(client: TestClient):
    """API：无法条数据时 GET /knowledge/laws 返回空数组。"""
    resp = client.get("/knowledge/laws")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == []
