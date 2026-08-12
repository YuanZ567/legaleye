"""Document ORM 表模型（M1 文件上传与解析核心实体）。

契约来源：
- 对外字段对齐 docs/DATA_CONTRACT.md 4.3 Documents；
- 敏感模式规则对齐 docs/PRD.md 第 6 章：raw_text 敏感模式下为 NULL，
  仅持久化解析文本摘要 text_fingerprint；
- user_id 为多用户隔离预留（M8 接入 auth 后启用）。
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Text, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.core.enums import DocType


class Document(SQLModel, table=True):
    """合规文档：上传/解析后的文档元数据与解析产物。"""

    __tablename__ = "documents"

    # ── 主键 / 归属 ──
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(default=None, index=True)  # M8 多用户隔离

    # ── 元数据（契约字段）──
    filename: str = Field(max_length=255, nullable=False)
    doc_type: DocType = Field(
        sa_column=Column(
            SAEnum(
                DocType,
                name="doc_type",
                native_enum=False,  # 存字符串 + CHECK，便于跨库迁移/巡检
                length=32,
                values_callable=lambda e: [m.value for m in e],  # 持久化 camelCase 值
            ),
            nullable=False,
        )
    )
    char_count: int = Field(default=0, nullable=False)
    text_preview: str | None = Field(default=None, max_length=500)  # 前 500 字
    sensitive_mode: bool = Field(default=False, nullable=False)

    # ── 解析产物 ──
    raw_text: str | None = Field(  # 敏感模式下必须为 NULL（PRD 第 6 章）
        default=None, sa_column=Column(Text, nullable=True)
    )
    text_fingerprint: str | None = Field(  # 敏感模式下存 sha256 摘要（64 字符）
        default=None, max_length=64
    )
    # 原始文件在 MinIO 的对象 key（默认模式存原文；敏感模式为 NULL，内部字段不对外暴露）
    minio_object_key: str | None = Field(default=None, max_length=255)

    # ── 审计 ──
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
