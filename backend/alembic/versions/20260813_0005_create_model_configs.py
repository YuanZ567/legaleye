"""create model_configs and llm_call_records tables

Revision ID: 20260813_0005
Revises: 20260812_0004
Create Date: 2026-08-13
"""

from alembic import op
import sqlalchemy as sa

from app.core.enums import Provider

# revision identifiers, used by Alembic.
revision: str = "20260813_0005"
down_revision: str = "20260812_0004"
branch_labels = None
depends_on = None


def _provider_enum() -> sa.Enum:
    return sa.Enum(
        Provider, name="provider", native_enum=False, length=32,
        values_callable=lambda e: [m.value for m in e],
    )


def upgrade() -> None:
    """创建模型配置表与 LLM 调用记账表。"""
    op.create_table(
        "model_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", _provider_enum(), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "llm_call_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("node", sa.String(length=32), nullable=True),
        sa.Column("provider", _provider_enum(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_est", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_call_records_task_id", "llm_call_records", ["task_id"])


def downgrade() -> None:
    """回滚：删除记账表与配置表。"""
    op.drop_index("ix_llm_call_records_task_id", table_name="llm_call_records")
    op.drop_table("llm_call_records")
    op.drop_table("model_configs")
