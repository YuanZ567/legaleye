"""任务路由（M4-5）：创建审查任务 + 详情 + SSE 进度流。

- POST /tasks：创建任务并分发 Celery（契约 DATA_CONTRACT 4.4）；
- GET  /tasks/{id}：任务详情；
- GET  /tasks/{id}/events：SSE 流式推送 taskStatus/nodeStart/nodeEnd/tokenUsage。
薄层：参数校验 + 调 services。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.db import get_db
from app.core.sse import iter_events
from app.models import User
from app.schemas.task import TaskCreateIn, TaskCreateOut, TaskOut
from app.services.task_service import (
    create_task,
    delete_task,
    dispatch_task,
    get_task,
    list_tasks,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _dump_task(task, db: Session | None = None) -> dict:
    """序列化任务核心字段（契约 TaskOut，findings 明细由详情端点单独提供）。

    M10：附带 documentFilename（关联文档原始文件名），任务卡片展示用。
    """
    data = TaskOut.model_validate(task, from_attributes=True).model_dump(by_alias=True)
    if db is not None and task.document_id is not None:
        from app.models import Document

        doc = db.get(Document, task.document_id)
        if doc is not None:
            data["documentFilename"] = doc.filename
    return data


@router.get("")
async def list_review_tasks(
    status: str | None = None,
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """列出审查任务（可按 status 筛选，倒序）。"""
    tasks = list_tasks(db=db, status=status)
    return {"data": [_dump_task(t, db) for t in tasks]}


@router.post("")
async def create_review_task(
    payload: TaskCreateIn,
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """创建审查任务并异步分发。

    demo 免 Key 用户每日限流 3 次（IP+user_id 双重限制，429 友好提示）；
    配自有 Key 的付费用户无限次。
    """
    if not payload.document_ids:
        raise HTTPException(status_code=400, detail="documentIds 不能为空")

    # 关联当前用户（demo 未登录 → None，归属校验时对 None 放行）
    user_id = _resolve_user_id(request)

    # M9-8 限流接线：配置了自有 Key 的付费用户无限次；无 Key 走 demo 限流 3 次/日
    from app.models import User
    from app.services.rate_limit_service import check_demo_limit

    client_ip = request.client.host if request.client else "unknown"
    has_personal_key = False
    if user_id is not None:
        user = db.get(User, user_id)
        has_personal_key = bool(user and user.api_key_encrypted)
    if not has_personal_key:
        check_demo_limit(ip=client_ip, user_id=str(user_id) if user_id else None)

    document_id = payload.document_ids[0]  # M4 单文件审查
    task_id = create_task(db=db, document_id=document_id, user_id=user_id)
    dispatch_task(task_id=task_id, document_id=document_id)
    return TaskCreateOut(task_id=task_id).model_dump(by_alias=True)


def _resolve_user_id(request: Request) -> uuid.UUID | None:
    """从 Authorization header 解析当前用户 id（无/无效 token → None，demo 模式）。"""
    import uuid as _uuid

    from app.core.auth import decode_access_token

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = decode_access_token(auth[7:])
        return _uuid.UUID(payload["sub"])
    except Exception:
        return None


@router.delete("/{task_id}")
async def delete_review_task(
    task_id: uuid.UUID,
    _admin: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """删除审查任务（admin 专属）；级联删除 findings + report（DB CASCADE）。"""
    ok = delete_task(db=db, task_id=task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"deleted": True}


@router.get("/{task_id}")
async def get_review_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """查询任务详情。"""
    task = get_task(db=db, task_id=task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"data": _dump_task(task, db)}


@router.get("/{task_id}/events")
async def stream_task_events(task_id: uuid.UUID) -> StreamingResponse:
    """SSE 流式推送任务进度事件（taskStatus/nodeStart/nodeEnd/tokenUsage）。"""
    return StreamingResponse(
        iter_events(str(task_id)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
