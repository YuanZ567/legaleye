"""create data_flow_entities and data_flow_edges tables

Revision ID: 20260812_0004
Revises: 20260812_0003
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op
from app.core.enums import EdgeType, EntityRole

# revision identifiers, used by Alembic.
revision: str = "20260812_0004"
down_revision: str = "20260812_0003"
branch_labels = None
depends_on = None


# 统一枚举持久化（与模型一致：存 camelCase 字符串）
def _entity_role_enum() -> sa.Enum:
    return sa.Enum(
        EntityRole,
        name="entity_role",
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )


def _edge_type_enum() -> sa.Enum:
    return sa.Enum(
        EdgeType,
        name="edge_type",
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )


def upgrade() -> None:
    """创建图谱实体表与边表（去重唯一约束：document+name+role / document+from+to+type）。"""
    op.create_table(
        "data_flow_entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", _entity_role_enum(), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "name", "role", name="uq_dataflow_entity_doc_name_role"),
    )
    op.create_index("ix_data_flow_entities_document_id", "data_flow_entities", ["document_id"])

    op.create_table(
        "data_flow_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("from_entity_id", sa.Uuid(), nullable=False),
        sa.Column("to_entity_id", sa.Uuid(), nullable=False),
        sa.Column("edge_type", _edge_type_enum(), nullable=False),
        sa.Column("legal_basis", sa.String(length=255), nullable=True),
        sa.Column("is_risk", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "from_entity_id",
            "to_entity_id",
            "edge_type",
            name="uq_dataflow_edge_doc_from_to_type",
        ),
    )
    op.create_index("ix_data_flow_edges_document_id", "data_flow_edges", ["document_id"])


def downgrade() -> None:
    """回滚：删除边表与实体表。"""
    op.drop_index("ix_data_flow_edges_document_id", table_name="data_flow_edges")
    op.drop_table("data_flow_edges")
    op.drop_index("ix_data_flow_entities_document_id", table_name="data_flow_entities")
    op.drop_table("data_flow_entities")
