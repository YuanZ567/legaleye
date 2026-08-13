"""create review_tasks and compliance_findings tables

Revision ID: 20260813_0006
Revises: 20260813_0005
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op
from app.core.enums import FindingLevel, FindingVerdict, ReviewDimension

# revision identifiers, used by Alembic.
revision: str = "20260813_0006"
down_revision: str = "20260813_0005"
branch_labels = None
depends_on = None


def _dimension_enum() -> sa.Enum:
    return sa.Enum(
        ReviewDimension,
        name="finding_dimension",
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )


def _verdict_enum() -> sa.Enum:
    return sa.Enum(
        FindingVerdict,
        name="finding_verdict",
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )


def _level_enum() -> sa.Enum:
    return sa.Enum(
        FindingLevel,
        name="finding_level",
        native_enum=False,
        length=16,
        values_callable=lambda e: [m.value for m in e],
    )


def upgrade() -> None:
    """创建审查任务表与合规发现表。"""
    op.create_table(
        "review_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("token_usage", sa.Integer(), nullable=False),
        sa.Column("finding_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_tasks_document_id", "review_tasks", ["document_id"])

    op.create_table(
        "compliance_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("dimension", _dimension_enum(), nullable=False),
        sa.Column("verdict", _verdict_enum(), nullable=False),
        sa.Column("level", _level_enum(), nullable=False),
        sa.Column("clause_ref", sa.String(length=64), nullable=False),
        sa.Column("statute_version", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("needs_human_review", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_findings_task_id", "compliance_findings", ["task_id"])
    op.create_foreign_key(
        "fk_compliance_findings_task",
        "compliance_findings",
        "review_tasks",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """回滚：删除合规发现表与审查任务表。"""
    op.drop_table("compliance_findings")
    op.drop_table("review_tasks")
