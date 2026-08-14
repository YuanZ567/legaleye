"""add user_id to review_tasks

Revision ID: 20260814_0009
Revises: 20260814_0008
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260814_0009"
down_revision: str = "20260814_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """给 review_tasks 增加 user_id（任务归属，多用户隔离）。"""
    op.add_column("review_tasks", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_index("ix_review_tasks_user_id", "review_tasks", ["user_id"])


def downgrade() -> None:
    """回滚：删除 user_id 列。"""
    op.drop_index("ix_review_tasks_user_id", table_name="review_tasks")
    op.drop_column("review_tasks", "user_id")
