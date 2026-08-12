"""Documents 契约模型（对齐 DATA_CONTRACT 4.3）。

Document 响应模型字段与后端 Document 表字段一一对应（snake_case 模型 → camelCase 契约）。
"""

import uuid
from datetime import datetime

from pydantic import Field

from app.core.enums import DocType
from app.schemas.base import APIModel


class UrlDocumentIn(APIModel):
    """from-url 请求契约（DATA_CONTRACT 4.3）：{url, docType}。

    url 保持原样（单字母无大小写转换）；docType 由 camelCase 别名绑定。
    """

    url: str = Field(..., min_length=1)
    doc_type: DocType = Field(..., alias="docType")


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
