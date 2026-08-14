"""模型配置路由（M8-3）：admin 专属。

契约（DATA_CONTRACT 4.2）：
- GET  /models                       → {data: ModelConfig[]}
- POST /models                       → {data: ModelConfig}（Key Fernet 存储 + apiKeyTail 脱敏）
- PUT  /models/{id}/activate         → {data: ModelConfig}（事务切换 active）
- POST /models/test                  → {data:{ok}}（真实打通 provider，无效 Key 保存前拦截）

所有端点需 admin 角色（require_admin）。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.db import get_db
from app.models import User
from app.schemas.model import ModelCreateIn, ModelTestIn, ModelTestOut
from app.services.model_service import (
    activate_model,
    create_model,
    list_models,
    test_model,
    to_dict,
)

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
async def get_models(
    _admin: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """列出模型配置（apiKeyTail 脱敏）。"""
    return {"data": list_models(db)}


@router.post("")
async def create_model_config(
    payload: ModelCreateIn,
    _admin: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """保存模型配置（Key Fernet 密文；apiKeyTail 脱敏；无效 Key 已在 test 拦截）。"""
    cfg = create_model(
        db=db, provider=payload.provider, api_key=payload.api_key, model=payload.model
    )
    return {"data": to_dict(cfg)}


@router.put("/{model_id}/activate")
async def activate_model_config(
    model_id: uuid.UUID,
    _admin: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """切换激活（事务：停用其他 active → 启用目标）。"""
    cfg = activate_model(db=db, model_id=model_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"data": to_dict(cfg)}


@router.post("/test")
async def test_model_config(
    payload: ModelTestIn,
    _admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """真实验证打通 provider（无效 Key 保存前拦截）。"""
    result = test_model(provider=payload.provider, api_key=payload.api_key, model=payload.model)
    return {"data": ModelTestOut(**result).model_dump(by_alias=True)}
