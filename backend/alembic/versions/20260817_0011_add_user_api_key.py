"""add api_key_encrypted/api_key_tail to users

Revision ID: 20260817_0011
Revises: 20260817_0010
Create Date: 2026-08-17
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260817_0011"
down_revision: str = "20260817_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """给 users 增加用户级 API Key 字段（Fernet 密文 + 尾号 4 位，明文不落库）。"""
    op.add_column("users", sa.Column("api_key_encrypted", sa.String(length=1024), nullable=True))
    op.add_column("users", sa.Column("api_key_tail", sa.String(length=8), nullable=True))


def downgrade() -> None:
    """回滚：删除用户级 API Key 字段。"""
    op.drop_column("users", "api_key_tail")
    op.drop_column("users", "api_key_encrypted")
