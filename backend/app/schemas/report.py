"""报告契约模型（DATA_CONTRACT 4.9 Report）。

嵌套 ComplianceFinding（4.8 完整契约，含 evidence）与 CrossDocConflict（4.11）。
CrossDocConflict 复用 crossdoc.py 的 schema，不重定义。
"""

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import APIModel
from app.schemas.crossdoc import CrossDocConflict


class FindingContract(APIModel):
    """ComplianceFinding 完整契约（4.8，含 evidence）。"""

    id: uuid.UUID
    task_id: uuid.UUID | None = Field(default=None, alias="taskId")
    dimension: str
    verdict: str
    level: str
    clause_ref: str = Field(default="", alias="clauseRef")
    statute_version: str | None = Field(default=None, alias="statuteVersion")
    description: str = ""
    remediation: str = ""
    confidence: float = 0.0
    needs_human_review: bool = Field(default=False, alias="needsHumanReview")
    evidence: dict | None = None  # {text, charRange}


class ReportOut(APIModel):
    """报告契约（4.9）：{taskId, summary, baselineVersion, generatedAt,
    findingCount, highRiskCount, findings, crossDocConflicts?}。"""

    task_id: uuid.UUID = Field(alias="taskId")
    summary: str
    baseline_version: str = Field(alias="baselineVersion")
    generated_at: datetime = Field(alias="generatedAt")
    finding_count: int = Field(alias="findingCount")
    high_risk_count: int = Field(alias="highRiskCount")
    findings: list[FindingContract] = Field(default_factory=list)
    cross_doc_conflicts: list[CrossDocConflict] = Field(
        default_factory=list, alias="crossDocConflicts"
    )
