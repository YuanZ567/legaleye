"""数据流图谱 ORM 模型（M3 数据流提取与图谱，PRD F6）。

契约来源（DATA_CONTRACT 4.7 GraphPayload）：
- DataFlowEntity 对应 entities（name/role/isSensitive）；
- DataFlowEdge 对应 edges（from/to/type/legalBasis/isRisk）；
- 去重规则（4.10 validators）：同 document+name+role 合并实体、同边合并。
"""

import uuid
from typing import Any

from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.core.enums import EdgeType, EntityRole


class DataFlowEntity(SQLModel, table=True):
    """图谱实体：数据流中的参与者/数据类型（controller/processor/trustee/overseasReceiver/dataCategory）。"""

    __tablename__ = "data_flow_entities"
    __table_args__ = (
        # 去重：同 document + name + role 唯一（DATA_CONTRACT 4.10 validators）
        UniqueConstraint("document_id", "name", "role", name="uq_dataflow_entity_doc_name_role"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID | None = Field(default=None, index=True)  # 关联 Document（M3-5 接 auth）
    name: str = Field(max_length=255, nullable=False)
    role: EntityRole = Field(
        sa_column=Column(
            SAEnum(
                EntityRole,
                name="entity_role",
                native_enum=False,
                length=32,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    is_sensitive: bool = Field(default=False, nullable=False)

    created_at: Any = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class DataFlowEdge(SQLModel, table=True):
    """图谱边：数据流转关系（collect/store/share/entrust/crossBorder/anonymize）。"""

    __tablename__ = "data_flow_edges"
    __table_args__ = (
        # 去重：同 document + from + to + type 唯一
        UniqueConstraint(
            "document_id",
            "from_entity_id",
            "to_entity_id",
            "edge_type",
            name="uq_dataflow_edge_doc_from_to_type",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID | None = Field(default=None, index=True)  # 关联 Document
    from_entity_id: uuid.UUID = Field(nullable=False)
    to_entity_id: uuid.UUID = Field(nullable=False)
    edge_type: EdgeType = Field(
        sa_column=Column(
            SAEnum(
                EdgeType,
                name="edge_type",
                native_enum=False,
                length=32,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    legal_basis: str | None = Field(default=None, max_length=255)
    is_risk: bool = Field(default=False, nullable=False)

    created_at: Any = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
