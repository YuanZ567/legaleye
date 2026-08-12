"""知识库路由（DATA_CONTRACT 4.10）：法条列表 + 语义检索。

- GET  /knowledge/laws         ?statute=&version= → {data: LawBaseline[]}
- POST /knowledge/laws/search  {query} → {data: {results: [...]}}
薄层：仅参数校验 + 调 services；无命中返回空列表（不编造）。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.knowledge.law_service import list_laws
from app.knowledge.retrieval import semantic_search
from app.llm.embeddings import get_embedding_provider
from app.schemas.law import (
    LawBaselineOut,
    LawSearchHit,
    LawSearchIn,
    LawSearchOut,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _dump_baseline(law) -> dict:
    return LawBaselineOut.model_validate(law, from_attributes=True).model_dump(by_alias=True)


@router.get("/laws")
async def get_laws(
    statute: str | None = Query(default=None),
    version: str | None = Query(default=None),
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """列出法条基线（可按 statute/version 过滤）。"""
    laws = list_laws(db=db, statute=statute, version=version)
    return {"data": [_dump_baseline(law) for law in laws]}


@router.post("/laws/search")
async def search_laws(
    payload: LawSearchIn,
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """语义检索法条：Top-5 命中；无命中返回空列表（不编造）。"""
    provider = get_embedding_provider()
    hits = semantic_search(db=db, query=payload.query, top_k=5, provider=provider)
    results = [
        LawSearchHit(
            clause_ref=h.clause_ref,
            statute_version=h.statute_version,
            article_text=h.article_text,
            score=h.score,
        )
        for h in hits
    ]
    return {"data": LawSearchOut(results=results).model_dump(by_alias=True)}
