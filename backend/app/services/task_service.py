"""任务服务（M4-5）：创建审查任务 + 分发 Celery + 查询。

契约（DATA_CONTRACT 4.4）：POST /tasks {documentIds, taskType} → {taskId}。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ReviewTask


def create_task(
    *, db: Session, document_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> uuid.UUID:
    """创建审查任务（status=queued，关联 user_id 归属），返回 task_id。"""
    task = ReviewTask(document_id=document_id, user_id=user_id, status="queued", progress=0)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task.id


def dispatch_task(task_id: uuid.UUID, document_id: uuid.UUID) -> None:
    """分发 Celery 异步审查（延迟导入避免循环依赖），传入任务 id 以更新状态。

    apply_async + 显式 kwargs 传参：避免 celery bind=True 任务的位置参数歧义
    （delay 位置传参曾导致 task_id 丢失、worker 侧新建任务记录）。
    """
    from app.tasks.review_task import run_review

    run_review.apply_async(args=[str(document_id)], kwargs={"task_id": str(task_id)})


def get_task(db: Session, task_id: uuid.UUID) -> ReviewTask | None:
    """查询任务详情。"""
    return db.get(ReviewTask, task_id)


def list_tasks(db: Session, status: str | None = None) -> list[ReviewTask]:
    """列出审查任务（按状态筛选，倒序）。"""
    stmt = select(ReviewTask).order_by(ReviewTask.created_at.desc())
    if status:
        stmt = stmt.where(ReviewTask.status == status)
    return list(db.scalars(stmt).all())


def delete_task(db: Session, task_id: uuid.UUID) -> bool:
    """删除审查任务（admin）。

    级联删除依赖 DB 外键 CASCADE（ComplianceFinding/Report 已配 ondelete=CASCADE），
    不手动逐表 DELETE。返回 True 表示删除成功；任务不存在返回 False。
    运行中/排队中的任务拒绝删除——Celery worker 仍在写 findings，
    删行会导致审查结束时外键违规、整场审查白跑。
    """
    task = db.get(ReviewTask, task_id)
    if task is None:
        return False
    if task.status in ("running", "queued"):
        from app.core.exceptions import ValidationError

        raise ValidationError("任务正在运行中，不可删除；请等待完成或失败后再删除", code="task_running")
    db.delete(task)
    db.commit()
    return True
