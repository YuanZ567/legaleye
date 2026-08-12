"""Documents 契约模型（对齐 DATA_CONTRACT 4.3）。

Document 响应模型字段与后端 Document 表字段一一对应（snake_case 模型 → camelCase 契约）。
"""

import uuid
from datetime import datetime

from app.core.enums import DocType
from app.schemas.base import APIModel


class DocumentOut(APIModel):
    """Document 响应契约（DATA_CONTRACT 4.3）。

    textPreview：解析文本前 500 字；敏感模式下仍返回（仅摘录，不含原文）。
    """

    id: uuid.UUID
    filename: str
    doc_type: DocType
    char_count: int
    text_preview: str | None
    sensitive_mode: bool
    created_at: datetime
