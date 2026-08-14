"""认证工具（M8）：密码哈希 + JWT（Fernet 加密外层）+ 鉴权依赖。

契约（DATA_CONTRACT 4.1 Auth / L2 规则）：
- 密码只存 bcrypt 哈希；
- token = JWT（含 user_id/role/过期）再经 Fernet 加密，验证时解密 → 验 JWT；
- FastAPI Depends 统一鉴权（get_current_user），付费端点强制登录，免 Key 端点绕过。
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.enums import UserRole
from app.core.security import decrypt_secret, encrypt_secret
from app.models import User

# token 过期（默认 24h）
TOKEN_EXPIRE_HOURS = 24

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """bcrypt 密码哈希。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验密码。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID, role: UserRole) -> str:
    """签发 JWT（含 user_id/role/过期），再 Fernet 加密外层返回。

    :return: Fernet 加密后的 token 串。
    """
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire,
    }
    jwt_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return encrypt_secret(jwt_token)


def decode_access_token(token: str) -> dict[str, Any]:
    """解密并验证 JWT，返回 payload；无效抛 401。"""
    try:
        jwt_token = decrypt_secret(token)
        payload = jwt.decode(jwt_token, get_settings().jwt_secret, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token 无效或已过期"
        ) from None


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """FastAPI 依赖：解析 Bearer token → 返回当前 User（未登录抛 401）。

    免 Key 端点（如 demo 审查）可注入匿名 user 或绕过此依赖。
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(credentials.credentials)
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """admin 角色依赖（L3 接口，前端仅 admin 可见 + 服务端强制校验）。"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要 admin 权限")
    return user
