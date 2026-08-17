"""add oauth_provider/oauth_id to users

Revision ID: 20260817_0010
Revises: 20260814_0009
Create Date: 2026-08-17
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260817_0010"
down_revision: str = "20260814_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """给 users 增加 OAuth 字段（provider + oauth_id 联合定位第三方账号）。"""
    op.add_column("users", sa.Column("oauth_provider", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("oauth_id", sa.String(length=128), nullable=True))
    op.create_index("ix_users_oauth_provider_id", "users", ["oauth_provider", "oauth_id"])


def downgrade() -> None:
    """回滚：删除 OAuth 字段。"""
    op.drop_index("ix_users_oauth_provider_id", table_name="users")
    op.drop_column("users", "oauth_id")
    op.drop_column("users", "oauth_provider")
