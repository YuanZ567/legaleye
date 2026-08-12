"""知识库契约模型（DATA_CONTRACT 4.10）。

- LawBaseline 列表（GET /knowledge/laws）；
- LawSearch 请求与结果（POST /knowledge/laws/search）。
"""

import uuid
from datetime import date, datetime

from pydantic import Field

from app.schemas.base import APIModel


class LawBaselineOut(APIModel):
    """LawBaseline 响应契约（4.10）。"""

    id: uuid.UUID
    statute: str
    article_no: str = Field(alias="articleNo")
    article_text: str = Field(alias="articleText")
    effective_date: date = Field(alias="effectiveDate")
    version: str
    source: str
    created_at: datetime


class LawSearchIn(APIModel):
    """检索请求（4.10）：{query}。"""

    query: str = Field(..., min_length=1, max_length=2000)


class LawSearchHit(APIModel):
    """检索命中项（4.10 results 元素）：{clauseRef, statuteVersion, articleText, score}。"""

    clause_ref: str = Field(alias="clauseRef")
    statute_version: str = Field(alias="statuteVersion")
    article_text: str = Field(alias="articleText")
    score: float


class LawSearchOut(APIModel):
    """检索响应：{data: {results: LawSearchHit[]}}。"""

    results: list[LawSearchHit] = Field(default_factory=list)
