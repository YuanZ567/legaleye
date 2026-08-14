"""认证路由（M8-1）：注册/登录/当前用户。

契约（DATA_CONTRACT 4.1 Auth）：
- POST /auth/register {email,password} → {data:{token,user}}
- POST /auth/login      {email,password} → {data:{token,user}}
- GET  /auth/me → {data:user}
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.auth import AuthIn, AuthOut, UserOut
from app.services.auth_service import login, register

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
