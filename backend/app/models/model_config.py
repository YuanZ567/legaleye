"""LLM 配置与调用记账 ORM（M4-1）。

契约来源：
- ModelConfig：provider（Provider 枚举）/ apiKeyEncrypted（Fernet 密文，L2 永不出 API）
  / model / isActive；
- LLMCallRecord：内部 L3 记账（provider/model/input/output tokens/cost/latency），
  仅仪表盘聚合。
"""

import uuid
from typing import Any

from sqlalchemy import Column, DateTime, Text, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.core.enums import Provider


class ModelConfig(SQLModel, table=True):
    """模型配置：provider + Fernet 加密的 API Key。"""

    __tablename__ = "model_configs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    provider: Provider = Field(
        sa_column=Column(
            SAEnum(
                Provider,
                name="provider",
                native_enum=False,
                length=32,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    api_key_encrypted: str = Field(sa_column=Column(Text, nullable=False))  # Fernet 密文，L2
    model: str = Field(max_length=64, nullable=False)
    is_active: bool = Field(default=True, nullable=False)

    created_at: Any = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class LLMCallRecord(SQLModel, table=True):
    """LLM 调用记账（L3，仅仪表盘聚合，不出明细 API）。"""

    __tablename__ = "llm_call_records"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task_id: uuid.UUID | None = Field(default=None, index=True)
    node: str | None = Field(default=None, max_length=32)  # 调用节点（如 d1/orchestrator）
    provider: Provider = Field(
        sa_column=Column(
            SAEnum(
                Provider,
                name="provider",
                native_enum=False,
                length=32,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    model: str = Field(max_length=64, nullable=False)
    input_tokens: int = Field(default=0, nullable=False)
    output_tokens: int = Field(default=0, nullable=False)
    cost_est: float = Field(default=0.0, nullable=False)
    latency_ms: int = Field(default=0, nullable=False)

    created_at: Any = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
