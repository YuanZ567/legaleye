"""User ORM（M8 账号）：email + 密码哈希 + 角色。

契约（DATA_CONTRACT 4.1 Auth / L2 规则）：
- 密码只存哈希（bcrypt），绝不存明文；
- role：UserRole（user/admin）；
- 首个注册用户自动为 admin（M8-1 验收）。
"""

import uuid
from typing import Any

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.core.enums import UserRole


class User(SQLModel, table=True):
    """账号：邮箱 + 密码哈希 + 角色。"""

    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(sa_column=Column(String(255), unique=True, index=True, nullable=False))
    password_hash: str = Field(sa_column=Column(String(255), nullable=False))
    role: UserRole = Field(
        sa_column=Column(
            SAEnum(
                UserRole,
                name="user_role",
                native_enum=False,
                length=16,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )

    # OAuth（M9-6：provider + oauth_id 联合定位第三方账号；邮箱用合成 {provider}_{id}@oauth.local）
    oauth_provider: str | None = Field(default=None, nullable=True)
    oauth_id: str | None = Field(default=None, nullable=True)

    created_at: Any = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
