"""审查任务与合规发现 ORM（M4 主链核心，契约 DATA_CONTRACT 4.4 / 4.8）。

- ReviewTask：任务状态机 queued→running→done/failed，progress/tokenUsage/findingCount/error；
- ComplianceFinding：六维审查结论，强字段（clauseRef 正则 / confidence [0,1] / 枚举）。
"""

import uuid
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlmodel import Field, SQLModel

from app.core.enums import FindingLevel, FindingVerdict, ReviewDimension


class ReviewTask(SQLModel, table=True):
    """审查任务（创建 → 六维并行 → 报告）。"""

    __tablename__ = "review_tasks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(nullable=False, index=True)

    # 状态机（DATA_CONTRACT 4.4）
    status: str = Field(
        default="queued", max_length=16, nullable=False
    )  # queued/running/done/failed
    progress: int = Field(default=0, nullable=False)  # 0-100
    token_usage: int = Field(default=0, nullable=False)
    finding_count: int = Field(default=0, nullable=False)
    error: str | None = Field(default=None, max_length=500)

    created_at: Any = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: Any = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
        )
    )


class ComplianceFinding(SQLModel, table=True):
    """合规发现（六维审查结论，强字段）。"""

    __tablename__ = "compliance_findings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("review_tasks.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )

    dimension: ReviewDimension = Field(
        sa_column=Column(
            SAEnum(
                ReviewDimension,
                name="finding_dimension",
                native_enum=False,
                length=32,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    verdict: FindingVerdict = Field(
        sa_column=Column(
            SAEnum(
                FindingVerdict,
                name="finding_verdict",
                native_enum=False,
                length=32,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    level: FindingLevel = Field(
        sa_column=Column(
            SAEnum(
                FindingLevel,
                name="finding_level",
                native_enum=False,
                length=16,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    clause_ref: str = Field(default="", max_length=64, nullable=False)  # 空/待补 表示无命中
    statute_version: str | None = Field(default=None, max_length=64)
    description: str = Field(sa_column=Column(Text, default="", nullable=False))
    remediation: str = Field(sa_column=Column(Text, default="", nullable=False))
    confidence: float = Field(default=0.0, nullable=False)  # [0,1]
    needs_human_review: bool = Field(default=False, nullable=False)

    created_at: Any = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
