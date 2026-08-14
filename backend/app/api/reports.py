"""报告路由（M9-1）。

契约（DATA_CONTRACT 4.9）：
- GET /reports/{task_id}               → JSON Report（用户认证 + 任务归属校验）
- GET /reports/{task_id}/export.md     → Markdown（text/markdown + attachment）

鉴权：get_current_user + 任务归属校验（用户只能看自己的报告，复用 M8 模式）。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models import ReviewTask, User
from app.services.report_service import get_report, report_out, to_markdown

router = APIRouter(prefix="/reports", tags=["reports"])


def _ensure_task_owned(db: Session, task_id: uuid.UUID, user: User) -> None:
    """任务归属校验：任务不存在 404；非本人 403。"""
    task = db.get(ReviewTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.user_id is not None and task.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看他人报告")


@router.get("/{task_id}")
async def get_report_json(
    task_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """返回报告 JSON（契约 4.9）。"""
    _ensure_task_owned(db, task_id, user)
    report = get_report(db, task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在，请先生成")
    return {"data": report_out(report)}


@router.get("/{task_id}/export.md")
async def export_report_markdown(
    task_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
):
    """导出 Markdown 报告（text/markdown + attachment）。"""
    _ensure_task_owned(db, task_id, user)
    report = get_report(db, task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在，请先生成")
    return PlainTextResponse(
        content=to_markdown(report),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="report-{task_id}.md"'},
    )
