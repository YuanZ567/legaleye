"""认证服务（M8-1）：注册/登录/当前用户。

- 首个注册用户自动为 admin（M8 验收），后续为 user；
- 密码 bcrypt 哈希存储，绝不存明文；
- 签发 Fernet 加密 JWT。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, hash_password, verify_password
from app.core.enums import UserRole
from app.core.exceptions import ValidationError
from app.models import User


def register(db: Session, email: str, password: str) -> tuple[User, str]:
    """注册：首个用户为 admin，后续为 user。返回 (user, token)。"""
    exists = db.scalar(select(User).where(User.email == email))
    if exists is not None:
        raise ValidationError("该邮箱已注册", code="email_taken")

    # 首个用户 → admin；后续 → user
    first = db.scalar(select(User.id).limit(1)) is None
    role = UserRole.ADMIN if first else UserRole.USER

    user = User(email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.role)
    return user, token


def login(db: Session, email: str, password: str) -> tuple[User, str]:
    """登录：校验邮箱/密码，返回 (user, token)。"""
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise ValidationError("邮箱或密码错误", code="invalid_credentials")
    token = create_access_token(user.id, user.role)
    return user, token


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def update_profile(
    db: Session,
    user: User,
    *,
    display_name: str | None = None,
    avatar: str | None = None,
) -> User:
    """更新显示名/头像（字段均可选；传 None 表示不改该项）。"""
    if display_name is not None:
        user.display_name = display_name.strip() or None
    if avatar is not None:
        user.avatar = avatar
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, *, old_password: str, new_password: str) -> None:
    """已登录改密：校验旧密码 → 写新哈希。"""
    if not verify_password(old_password, user.password_hash):
        raise ValidationError("旧密码错误", code="invalid_credentials")
    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()


def reset_password(db: Session, *, email: str, new_password: str) -> None:
    """忘记密码：按注册邮箱直接重置（本项目无邮件服务；生产应改为邮件验证码）。

    邮箱不存在时同样返回成功语义之外——这里选择抛错以便前端提示用户检查邮箱，
    注册/登录页均可引导。
    """
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise ValidationError("该邮箱未注册", code="email_not_found")
    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()
