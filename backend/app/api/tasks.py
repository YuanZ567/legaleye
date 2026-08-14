"""任务路由（M4-5）：创建审查任务 + 详情 + SSE 进度流。

- POST /tasks：创建任务并分发 Celery（契约 DATA_CONTRACT 4.4）；
- GET  /tasks/{id}：任务详情；
- GET  /tasks/{id}/events：SSE 流式推送 taskStatus/nodeStart/nodeEnd/tokenUsage。
薄层：参数校验 + 调 services。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.sse import iter_events
from app.schemas.task import TaskCreateIn, TaskCreateOut, TaskOut
from app.services.task_service import (
    create_task,
    dispatch_task,
    get_task,
    list_tasks,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _dump_task(task) -> dict:
    """序列化任务核心字段（契约 TaskOut，findings 明细由详情端点单独提供）。"""
    return TaskOut.model_validate(task, from_attributes=True).model_dump(by_alias=True)


@router.get("")
async def list_review_tasks(
    status: str | None = None,
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """列出审查任务（可按 status 筛选，倒序）。"""
    tasks = list_tasks(db=db, status=status)
    return {"data": [_dump_task(t) for t in tasks]}


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

    # demo 限流（未登录/无 Key → 按 IP 计数；已登录 → user_id 优先）
    from app.services.rate_limit_service import check_demo_limit

    client_ip = request.client.host if request.client else "unknown"
    check_demo_limit(ip=client_ip, user_id=None)

    document_id = payload.document_ids[0]  # M4 单文件审查
    task_id = create_task(db=db, document_id=document_id)
    dispatch_task(task_id=task_id, document_id=document_id)
    return TaskCreateOut(task_id=task_id).model_dump(by_alias=True)


@router.get("/{task_id}")
async def get_review_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """查询任务详情。"""
    task = get_task(db=db, task_id=task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"data": _dump_task(task)}


@router.get("/{task_id}/events")
async def stream_task_events(task_id: uuid.UUID) -> StreamingResponse:
    """SSE 流式推送任务进度事件（taskStatus/nodeStart/nodeEnd/tokenUsage）。"""
    return StreamingResponse(
        iter_events(str(task_id)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
