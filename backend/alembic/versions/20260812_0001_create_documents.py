"""create documents table

Revision ID: 20260812_0001
Revises:
Create Date: 2026-08-12
"""

from alembic import op
import sqlalchemy as sa

from app.core.enums import DocType

# revision identifiers, used by Alembic.
revision: str = "20260812_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 documents 表（对齐 app/models/document.py 的 Document 模型）。"""
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column(
            "doc_type",
            sa.Enum(
                DocType,
                name="doc_type",
                native_enum=False,
                length=32,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        ),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("text_preview", sa.String(length=500), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("text_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("sensitive_mode", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])


def downgrade() -> None:
    """回滚：删除 documents 表。"""
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_table("documents")
