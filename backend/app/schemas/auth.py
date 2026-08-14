"""认证契约模型（DATA_CONTRACT 4.1 Auth）。"""

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.core.enums import UserRole
from app.schemas.base import APIModel


class AuthIn(APIModel):
    """注册/登录请求：{email, password}。"""

    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserOut(APIModel):
    """User 响应契约（4.1）：{id, email, role, createdAt}。"""

    id: uuid.UUID
    email: str
    role: UserRole
    created_at: datetime = Field(alias="createdAt")


class AuthOut(APIModel):
    """认证响应：{token, user}。"""

    token: str
    user: UserOut
