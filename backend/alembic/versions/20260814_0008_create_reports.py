"""create reports table

Revision ID: 20260814_0008
Revises: 20260814_0007
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260814_0008"
down_revision: str = "20260814_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 reports 表（task_id 唯一约束：一任务一报告）。"""
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("md_export", sa.String(), nullable=False),
        sa.Column("baseline_version", sa.String(length=32), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", name="uq_reports_task_id"),
    )
    op.create_index("ix_reports_task_id", "reports", ["task_id"])
    op.create_foreign_key(
        "fk_reports_task", "reports", "review_tasks", ["task_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    """回滚：删除 reports 表。"""
    op.drop_table("reports")
