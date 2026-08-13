"""任务服务（M4-5）：创建审查任务 + 分发 Celery + 查询。

契约（DATA_CONTRACT 4.4）：POST /tasks {documentIds, taskType} → {taskId}。
"""

import uuid

from sqlalchemy.orm import Session

from app.models import ReviewTask


def create_task(*, db: Session, document_id: uuid.UUID) -> uuid.UUID:
    """创建审查任务（status=queued），返回 task_id。"""
    task = ReviewTask(document_id=document_id, status="queued", progress=0)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task.id


def dispatch_task(task_id: uuid.UUID, document_id: uuid.UUID) -> None:
    """分发 Celery 异步审查（延迟导入避免循环依赖），传入任务 id 以更新状态。"""
    from app.tasks.review_task import run_review

    run_review.delay(str(document_id), str(task_id))


def get_task(db: Session, task_id: uuid.UUID) -> ReviewTask | None:
    """查询任务详情。"""
    return db.get(ReviewTask, task_id)
