"""审查任务契约模型（DATA_CONTRACT 4.4）。"""

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import APIModel


class TaskCreateIn(APIModel):
    """创建任务请求：{documentIds: [uuid], taskType?}。"""

    document_ids: list[uuid.UUID] = Field(alias="documentIds")
    task_type: str = Field(default="compliance", alias="taskType")


class TaskOut(APIModel):
    """审查任务响应契约（4.4 核心字段）。"""

    id: uuid.UUID
    status: str
    progress: int
    token_usage: int = Field(default=0, alias="tokenUsage")
    finding_count: int = Field(default=0, alias="findingCount")
    error: str | None = None
    created_at: datetime = Field(alias="createdAt")


class TaskCreateOut(APIModel):
    """创建任务响应：{taskId}。"""

    task_id: uuid.UUID = Field(alias="taskId")
