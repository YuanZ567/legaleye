"""create users table

Revision ID: 20260814_0007
Revises: 20260813_0006
Create Date: 2026-08-14
"""

import sqlalchemy as sa
from alembic import op
from app.core.enums import UserRole

# revision identifiers, used by Alembic.
revision: str = "20260814_0007"
down_revision: str = "20260813_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 users 表（密码哈希 + 角色，email 唯一）。"""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                UserRole,
                name="user_role",
                native_enum=False,
                length=16,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    """回滚：删除 users 表。"""
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
