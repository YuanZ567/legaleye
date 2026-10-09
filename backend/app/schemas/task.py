"""审查任务契约模型（DATA_CONTRACT 4.4）。"""

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import APIModel


class TaskCreateIn(APIModel):
    """创建任务请求：{documentIds: [uuid], taskType?}。"""

    document_ids: list[uuid.UUID] = Field(alias="documentIds")
    task_type: str = Field(default="compliance", alias="taskType")


class FindingOut(APIModel):
    """合规发现契约（DATA_CONTRACT 4.2 ComplianceFinding 核心字段）。"""

    id: uuid.UUID
    dimension: str
    verdict: str
    level: str = Field(alias="riskLevel")
    clause_ref: str = Field(default="", alias="clauseRef")
    statute_version: str | None = Field(default=None, alias="statuteVersion")
    description: str = ""
    remediation: str = ""
    confidence: float = 0.0
    needs_human_review: bool = Field(default=False, alias="needsHumanReview")


class TaskOut(APIModel):
    """审查任务响应契约（4.4 核心字段 + findings 明细）。"""

    id: uuid.UUID
    status: str
    progress: int
    document_id: uuid.UUID | None = Field(default=None, alias="documentId")
    # 关联文档的原始文件名（列表/卡片展示用；文档已删除 → None）
    document_filename: str | None = Field(default=None, alias="documentFilename")
    token_usage: int = Field(default=0, alias="tokenUsage")
    finding_count: int = Field(default=0, alias="findingCount")
    findings: list[FindingOut] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(alias="createdAt")


class TaskCreateOut(APIModel):
    """创建任务响应：{taskId}。"""

    task_id: uuid.UUID = Field(alias="taskId")
