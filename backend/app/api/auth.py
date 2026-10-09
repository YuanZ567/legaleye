"""认证路由（M8-1，M10+ 扩展账户管理）。

契约（DATA_CONTRACT 4.1 Auth）：
- POST /auth/register {email,password} → {data:{token,user}}
- POST /auth/login      {email,password} → {data:{token,user}}
- GET  /auth/me → {data:user}
- PATCH /auth/me        {displayName?,avatar?} → {data:user}（账户管理）
- POST /auth/change-password {oldPassword,newPassword} → {data:{ok:true}}
- POST /auth/reset-password  {email,newPassword} → {data:{ok:true}}（忘记密码）
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.core.exceptions import ValidationError
from app.models import User
from app.schemas.auth import (
    AuthIn,
    AuthOut,
    ChangePasswordIn,
    ResetPasswordIn,
    UpdateProfileIn,
    UserOut,
)
from app.services.auth_service import (
    change_password,
    login,
    register,
    reset_password,
    update_profile,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_out(user: User, token: str) -> dict:
    return AuthOut(
        token=token,
        user=UserOut.model_validate(user, from_attributes=True),
    ).model_dump(by_alias=True)


@router.post("/register")
async def register_account(payload: AuthIn, db: Session = Depends(get_db)) -> dict:  # noqa: B008
    """注册（首个用户为 admin）。"""
    user, token = register(db=db, email=payload.email, password=payload.password)
    return {"data": _auth_out(user, token)}


@router.post("/login")
async def login_account(payload: AuthIn, db: Session = Depends(get_db)) -> dict:  # noqa: B008
    """登录。"""
    user, token = login(db=db, email=payload.email, password=payload.password)
    return {"data": _auth_out(user, token)}


@router.get("/me")
async def me(user: Annotated[User, Depends(get_current_user)]) -> dict:
    """当前用户信息。"""
    return {"data": UserOut.model_validate(user, from_attributes=True).model_dump(by_alias=True)}


@router.patch("/me")
async def update_me(
    payload: UpdateProfileIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),  # noqa: B008
) -> dict:
    """账户管理：更新显示名/头像（至少传一项）。"""
    if payload.display_name is None and payload.avatar is None:
        raise ValidationError("至少提供 displayName 或 avatar", code="nothing_to_update")
    updated = update_profile(
        db, user, display_name=payload.display_name, avatar=payload.avatar
    )
    return {"data": UserOut.model_validate(updated, from_attributes=True).model_dump(by_alias=True)}


@router.post("/change-password")
async def change_own_password(
    payload: ChangePasswordIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),  # noqa: B008
) -> dict:
    """账户管理：已登录改密（需旧密码）。"""
    change_password(
        db, user, old_password=payload.old_password, new_password=payload.new_password
    )
    return {"data": {"ok": True}}


@router.post("/reset-password")
async def reset_own_password(payload: ResetPasswordIn, db: Session = Depends(get_db)) -> dict:  # noqa: B008
    """忘记密码：按注册邮箱重置（无邮件服务的轻量实现）。"""
    reset_password(db, email=payload.email, new_password=payload.new_password)
    return {"data": {"ok": True}}
