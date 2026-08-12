"""create law_baselines table + enable pgvector extension

Revision ID: 20260812_0003
Revises: 20260812_0002
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID as PgUUID

# revision identifiers, used by Alembic.
revision: str = "20260812_0003"
down_revision: str = "20260812_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """启用 pgvector 扩展并创建 law_baselines 表。

    唯一约束 statute+article_no+version（TODO 不允许破坏）；
    embedding 为 pgvector 向量列（1536 维，对齐百炼 embedding）。
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "law_baselines",
        sa.Column("id", PgUUID(), nullable=False),
        sa.Column("statute", sa.String(length=100), nullable=False),
        sa.Column("article_no", sa.String(length=32), nullable=False),
        sa.Column("article_text", sa.String(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "statute", "article_no", "version", name="uq_law_statute_article_version"
        ),
    )
    op.create_index("ix_law_baselines_statute", "law_baselines", ["statute"])


def downgrade() -> None:
    """回滚：删除表（保留 vector 扩展，避免误删其他表依赖）。"""
    op.drop_index("ix_law_baselines_statute", table_name="law_baselines")
    op.drop_table("law_baselines")
