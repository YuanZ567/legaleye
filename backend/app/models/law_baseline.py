"""LawBaseline ORM 表模型（M2 法条基线入库，PRD F9 / ARCHITECTURE 4.1）。

契约来源：
- 对外字段对齐 docs/DATA_CONTRACT.md 4.10 LawBaseline（statute/articleNo/articleText/
  effectiveDate/version/source）；
- 唯一约束 statute+article_no+version（TODO M2 不允许破坏）：同一法条修订时新增版本而非覆盖；
- embedding 向量列用于 M2-5 语义检索（pgvector）；向量维度对齐 M4 百炼 embedding 模型（1536）。
"""

import uuid
from datetime import date
from typing import Any

# pgvector 的 Vector 类型（SQLModel 通过 sa_column 挂载原生列类型）
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Date, DateTime, String, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class LawBaseline(SQLModel, table=True):
    """法条基线：结构化条款 + 版本化 + 向量检索。"""

    __tablename__ = "law_baselines"
    __table_args__ = (
        # 不允许破坏的唯一约束：同一法条 + 条款号 + 版本唯一
        UniqueConstraint("statute", "article_no", "version", name="uq_law_statute_article_version"),
    )

    # ── 主键 / 法条标识 ──
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    statute: str = Field(max_length=100, index=True, nullable=False)  # 法规名（如 个人信息保护法）
    article_no: str = Field(max_length=32, nullable=False)  # 条款号（clauseRef 正则格式）
    article_text: str = Field(sa_column=Column(String, nullable=False))  # 条款原文

    # ── 版本化 ──
    version: str = Field(max_length=32, nullable=False)  # 如 laws-v1.0-20260811
    effective_date: date = Field(sa_column=Column(Date, nullable=False))  # 生效日
    source: str = Field(max_length=255, nullable=False)  # 来源/出处

    # ── 语义检索向量（M2-5 用；维度对齐 embedding 模型）──
    embedding: Any | None = Field(
        default=None,
        sa_column=Column(Vector(1536), nullable=True),
    )

    # ── 审计 ──
    created_at: Any = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<LawBaseline {self.statute} {self.article_no} v{self.version}>"
