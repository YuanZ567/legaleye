"""用户级 API Key 服务（M9-8）：谁用谁付费。

红线（M9-8）：
- Key 只存 Fernet 密文（api_key_encrypted）+ 尾号 4 位（api_key_tail），明文绝不落库/出 API；
- 用户只能读写自己的 Key（调用方已用 get_current_user 保证归属）；
- 解密只在 worker 内存用（get_user_api_key_plain），不落日志。
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.security import decrypt_secret, encrypt_secret
from app.models import User


def set_api_key(db: Session, user: User, plain_key: str) -> str:
    """设置用户 API Key：校验非空 → Fernet 加密 + 存尾号 4 位。返回尾号（含 **** 前缀）。"""
    key = (plain_key or "").strip()
    if not key:
        raise ValidationError("API Key 不能为空", code="api_key_empty")
    user.api_key_encrypted = encrypt_secret(key)
    user.api_key_tail = key[-4:]
    db.add(user)
    db.commit()
    db.refresh(user)
    return f"****{user.api_key_tail}"


def clear_api_key(db: Session, user: User) -> None:
    """清除用户 API Key（两字段置空）。"""
    user.api_key_encrypted = None
    user.api_key_tail = None
    db.add(user)
    db.commit()


def get_user_api_key_plain(db: Session, user: User) -> str | None:
    """取用户 API Key 明文（worker 用；未配置返回 None）。"""
    if not user.api_key_encrypted:
        return None
    return decrypt_secret(user.api_key_encrypted)
