"""Report ORM（M9-1 报告生成）。

契约（DATA_CONTRACT 4.9）：
- content_json：Report 完整 JSON（{taskId, summary, baselineVersion, generatedAt,
  findingCount, highRiskCount, findings, crossDocConflicts?}）；
- md_export：Markdown 全文（朴素序列化，M9-3 完善）；
- baseline_version：锁存生成时的法规库版本（从 config 读，禁止硬编码）；
- task_id 唯一约束：一任务一报告（幂等 upsert）。
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class Report(SQLModel, table=True):
    """审查报告（一任务一报告，task_id 唯一）。"""

    __tablename__ = "reports"
    __table_args__ = (
        # 一任务一报告（不允许破坏）
        UniqueConstraint("task_id", name="uq_reports_task_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("review_tasks.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    content_json: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    md_export: str = Field(sa_column=Column(String, nullable=False))
    baseline_version: str = Field(max_length=32, nullable=False)

    generated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
