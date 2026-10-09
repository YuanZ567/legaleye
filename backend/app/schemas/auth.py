"""认证契约模型（DATA_CONTRACT 4.1 Auth）。"""

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.core.enums import UserRole
from app.schemas.base import APIModel


class AuthIn(APIModel):
    """注册/登录请求：{email, password}。"""

    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserOut(APIModel):
    """User 响应契约（4.1）：{id, email, role, createdAt, apiKeyTail, displayName, avatar}。"""

    id: uuid.UUID
    email: str
    role: UserRole
    created_at: datetime = Field(alias="createdAt")
    # M9-8：用户级 API Key 尾号（未配置 → null；展示格式统一 **** 前缀）
    api_key_tail: str | None = Field(default=None, alias="apiKeyTail")
    # M10+ 账户管理：显示名（未设置 → null，前端回退邮箱前缀）+ emoji 头像
    display_name: str | None = Field(default=None, alias="displayName")
    avatar: str | None = None

    @field_validator("api_key_tail")
    @classmethod
    def _mask_tail(cls, v: str | None) -> str | None:
        """尾号统一为展示格式 `****abcd`（存储为纯 4 位，出 API 加掩码前缀）。"""
        if not v:
            return None
        return f"****{v}"


class UpdateProfileIn(APIModel):
    """PATCH /auth/me 请求：更新显示名/头像（均可选，至少一项）。"""

    display_name: str | None = Field(
        default=None, alias="displayName", min_length=1, max_length=64
    )
    avatar: str | None = Field(default=None, min_length=1, max_length=16)


class ChangePasswordIn(APIModel):
    """POST /auth/change-password 请求：旧密码 + 新密码（已登录改密）。"""

    old_password: str = Field(..., alias="oldPassword", min_length=6, max_length=128)
    new_password: str = Field(..., alias="newPassword", min_length=6, max_length=128)


class ResetPasswordIn(APIModel):
    """POST /auth/reset-password 请求：忘记密码 → 按注册邮箱重置（无邮件服务，邮箱验证）。"""

    email: EmailStr
    new_password: str = Field(..., alias="newPassword", min_length=6, max_length=128)


class AuthOut(APIModel):
    """认证响应：{token, user}。"""

    token: str
    user: UserOut
