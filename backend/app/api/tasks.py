"""任务路由（M4-5）：创建审查任务 + 详情 + SSE 进度流。

- POST /tasks：创建任务并分发 Celery（契约 DATA_CONTRACT 4.4）；
- GET  /tasks/{id}：任务详情；
- GET  /tasks/{id}/events：SSE 流式推送 taskStatus/nodeStart/nodeEnd/tokenUsage。
薄层：参数校验 + 调 services。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.sse import iter_events
from app.schemas.task import TaskCreateIn, TaskCreateOut, TaskOut
from app.services.task_service import create_task, dispatch_task, get_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _dump_task(task) -> dict:
    """序列化任务 + 关联 findings（API 契约：findings 明细）。"""
    from app.core.db import SessionLocal
    from app.models import ComplianceFinding

    with SessionLocal() as session:
        findings = (
            session.query(ComplianceFinding)
            .filter(ComplianceFinding.task_id == task.id)
            .order_by(ComplianceFinding.created_at)
            .all()
        )
    return TaskOut.model_validate(
        task, from_attributes=True
    ).model_copy(update={"findings": findings}).model_dump(by_alias=True)


@router.post("")
async def create_review_task(
    payload: TaskCreateIn,
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """创建审查任务并异步分发。"""
    if not payload.document_ids:
        raise HTTPException(status_code=400, detail="documentIds 不能为空")
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
