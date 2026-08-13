"""跨文档联合审查契约模型（DATA_CONTRACT 4.8 CrossDocConflict）。"""

import uuid

from pydantic import Field

from app.core.enums import DeclarationKey, RiskLevel
from app.schemas.base import APIModel


class DocDeclaration(APIModel):
    """单侧文档的声明值 + 原文证据（docA/docB）。"""

    document_id: uuid.UUID = Field(alias="documentId")
    value: str
    evidence: dict | None = None  # {text, charRange}


class CrossDocConflict(APIModel):
    """跨文档矛盾（4.8）：声明键 + 两侧文档声明 + 矛盾级别。"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task_id: uuid.UUID | None = Field(default=None, alias="taskId")
    declaration_key: DeclarationKey = Field(alias="declarationKey")
    doc_a: DocDeclaration = Field(alias="docA")
    doc_b: DocDeclaration = Field(alias="docB")
    level: RiskLevel
