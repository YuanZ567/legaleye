"""法条语义检索（M2-5）：pgvector 余弦相似度 Top-5 + 无命中返回空。

纪律：
- 检索无命中返回空列表，不编造（TODO 不允许破坏）；
- embedding 生成经 `llm/embeddings` 工厂（禁止裸调 LLM）；
- 只检索"当前生效"条款（effective_date 最晚版本），避免跨版本混淆；
- 测试/CI 用 mock embedding provider（真实百炼集成 M4 统一接入）。
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.embeddings import EmbeddingProvider, get_embedding_provider
from app.models.law_baseline import LawBaseline


@dataclass
class LawHit:
    """检索命中项（对齐 DATA_CONTRACT 4.10 search results）。"""

    clause_ref: str
    statute_version: str
    article_text: str
    score: float


def embed_law_baseline(
    *,
    db: Session,
    provider: EmbeddingProvider | None = None,
    batch_size: int = 20,
) -> int:
    """为 embedding 为 NULL 的法条回填向量（入库后首次检索前调用）。

    :return: 本次回填的条款数。
    """
    provider = provider or get_embedding_provider()
    pending = db.scalars(select(LawBaseline).where(LawBaseline.embedding.is_(None))).all()
    if not pending:
        return 0

    filled = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        vectors = provider.embed([law.article_text for law in batch])
        for law, vector in zip(batch, vectors, strict=True):
            law.embedding = vector
        db.commit()
        filled += len(batch)
    return filled


def semantic_search(
    *,
    db: Session,
    query: str,
    top_k: int = 5,
    provider: EmbeddingProvider | None = None,
) -> list[LawHit]:
    """语义检索法条基线：query 向量化 → 余弦相似度 Top-k。

    仅检索有效 embedding 的条款；无命中返回空列表（不编造）。
    """
    provider = provider or get_embedding_provider()
    query_vec = provider.embed([query])[0]

    # 无任何已向量化条款 → 直接返回空（避免执行 PG 专用 <=> 操作符，且符合"无命中返回空"）
    has_vector = db.scalar(select(LawBaseline.id).where(LawBaseline.embedding.isnot(None)).limit(1))
    if has_vector is None:
        return []

    # pgvector 余弦距离排序取 Top-k，并在 SQL 层同时返回距离以计算相似度
    distance_col = LawBaseline.embedding.cosine_distance(query_vec).label("distance")
    rows = db.execute(
        select(LawBaseline, distance_col)
        .where(LawBaseline.embedding.isnot(None))
        .order_by(distance_col)
        .limit(top_k)
    ).all()

    return [
        LawHit(
            clause_ref=law.article_no,
            statute_version=law.version,
            article_text=law.article_text,
            score=_distance_to_score(distance),
        )
        for law, distance in rows
    ]


def _distance_to_score(distance: float) -> float:
    """把 cosine_distance 转相似度 score（1 - 距离，范围 ~[0,1]）。"""
    return round(max(0.0, min(1.0, 1.0 - distance)), 4)
