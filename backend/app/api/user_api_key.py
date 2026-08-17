"""用户级 API Key 路由（M9-8）：谁用谁付费。

- PUT    /users/me/api-key  {apiKey} → {data:{apiKeyTail}}
- DELETE /users/me/api-key            → {data:{cleared:true}}

鉴权：登录用户（get_current_user）操作自己的 Key，无需 admin。
Key 只存 Fernet 密文 + 尾号，响应/日志绝不含明文。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.base import APIModel
from app.services.user_api_key_service import clear_api_key, set_api_key

router = APIRouter(prefix="/users/me", tags=["user-api-key"])


class ApiKeyIn(APIModel):
    """设置 API Key 请求：{apiKey}。"""

    api_key: str = Field(..., min_length=1, max_length=1024, alias="apiKey")


class ApiKeyTailOut(APIModel):
    """设置成功响应：{apiKeyTail}。"""

    api_key_tail: str = Field(alias="apiKeyTail")


class ApiKeyClearOut(APIModel):
    """清除成功响应：{cleared}。"""

    cleared: bool


@router.put("/api-key")
async def set_my_api_key(
    payload: ApiKeyIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """设置自己的 API Key（Fernet 加密 + 尾号）。"""
    tail = set_api_key(db=db, user=user, plain_key=payload.api_key)
    return {"data": ApiKeyTailOut(api_key_tail=tail).model_dump(by_alias=True)}


@router.delete("/api-key")
async def delete_my_api_key(
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """清除自己的 API Key。"""
    clear_api_key(db=db, user=user)
    return {"data": ApiKeyClearOut(cleared=True).model_dump(by_alias=True)}
