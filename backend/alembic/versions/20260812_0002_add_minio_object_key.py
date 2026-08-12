"""add minio_object_key to documents

Revision ID: 20260812_0002
Revises: 20260812_0001
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260812_0002"
down_revision: str = "20260812_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """给 documents 增加原始文件 MinIO 对象 key（敏感模式为 NULL）。"""
    op.add_column("documents", sa.Column("minio_object_key", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """回滚：删除 minio_object_key 列。"""
    op.drop_column("documents", "minio_object_key")
