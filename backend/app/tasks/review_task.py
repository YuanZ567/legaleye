"""审查任务（M4-3）：Celery 异步执行 LangGraph 审查工作流。

流程：读 Document → 标记 running → 跑工作流（orchestrator + D1-D6 + 反思 + report）
→ 写 ComplianceFinding → 标记 done。
降级容错（ARCHITECTURE 6.4）：工作流异常/超时 → 标记 failed，并写入一条
"待补 + needsHumanReview=true" 的降级 finding，任务不中断。
"""

import asyncio
import logging
import uuid

from app.agents.workflow import build_workflow
from app.core.db import SessionLocal
from app.core.enums import FindingLevel, FindingVerdict, ReviewDimension
from app.core.sse import publish_event
from app.models import ComplianceFinding, Document, ReviewTask
from app.services.report_service import generate_report
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_DEGRADED_DIMENSIONS = [d for d in ReviewDimension]


@celery_app.task(bind=True, max_retries=2)
def run_review(self, document_id: str, task_id: str | None = None) -> dict:
    """执行一次完整审查（异步任务；max_retries=2 对应"重试 2 次"）。

    :param task_id: API 创建的任务 id（更新该任务状态与 findings）；None 则新建。
    """
    tid = uuid.UUID(task_id) if task_id else uuid.uuid4()
    try:
        _run_workflow(task_id=tid, document_id=uuid.UUID(document_id))
        return {"task_id": str(tid), "status": "done"}
    except Exception as exc:
        logger.exception("审查失败，尝试降级: %s", exc)
        # 重试 2 次仍失败 → 降级（不中断任务）
        try:
            _degrade_task(task_id=tid, document_id=uuid.UUID(document_id))
            return {"task_id": str(tid), "status": "degraded"}
        except Exception:
            # 降级也失败：标记任务 failed
            _mark_failed(tid, str(exc))
            return {"task_id": str(tid), "status": "failed"}


def _run_workflow(*, task_id: uuid.UUID, document_id: uuid.UUID) -> None:
    """运行 LangGraph 工作流并落库 findings。"""
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        if doc is None:
            raise ValueError(f"文档不存在: {document_id}")
        text = doc.raw_text or ""
        # upsert：若 API 已创建该任务则更新状态，否则新建
        task = db.get(ReviewTask, task_id)
        if task is None:
            task = ReviewTask(id=task_id, document_id=document_id, status="running", progress=10)
            db.add(task)
        else:
            task.status = "running"
            task.progress = 10
        db.commit()
        publish_event(str(task_id), "taskStatus", {"status": "running", "progress": 10})

    graph = build_workflow()
    # LangGraph 是 async 图，用 asyncio.run 同步驱动（Celery worker 内）
    state = asyncio.run(
        graph.ainvoke(
            {
                "task_id": str(task_id),
                "document_id": str(document_id),
                "document_text": text,
            }
        )
    )

    findings = state.get("findings", [])
    with SessionLocal() as db:
        t = db.get(ReviewTask, task_id)
        for f in findings:
            dim = f["dimension"]
            db.add(
                ComplianceFinding(
                    task_id=task_id,
                    dimension=ReviewDimension(dim) if dim in ReviewDimension.__members__ else dim,
                    verdict=FindingVerdict(f.get("verdict", "unclear")),
                    level=FindingLevel(f.get("level", "medium")),
                    clause_ref=f.get("clauseRef", ""),
                    statute_version=f.get("statuteVersion"),
                    description=f.get("description", ""),
                    remediation=f.get("remediation", ""),
                    confidence=float(f.get("confidence", 0.0)),
                    needs_human_review=bool(f.get("needsHumanReview", False)),
                )
            )
        if t is not None:
            t.status = "done"
            t.progress = 100
            t.finding_count = len(findings)
        db.commit()
        # M9 集成：任务完成后生成报告（幂等 upsert，一任务一报告）
        generate_report(db=db, task_id=task_id)


def _degrade_task(*, task_id: uuid.UUID, document_id: uuid.UUID) -> None:
    """降级：任务不中断，写入"待补 + needsHumanReview=true"的 finding。"""
    with SessionLocal() as db:
        task = db.get(ReviewTask, task_id)
        if task is None:
            task = ReviewTask(id=task_id, document_id=document_id, status="done", progress=100)
            db.add(task)
        else:
            task.status = "done"
            task.progress = 100
        task.finding_count = len(_DEGRADED_DIMENSIONS)
        for dim in _DEGRADED_DIMENSIONS:
            db.add(
                ComplianceFinding(
                    task_id=task_id,
                    dimension=dim,
                    verdict=FindingVerdict.UNCLEAR,
                    level=FindingLevel.LOW,
                    clause_ref="待补",
                    description="LLM 调用失败，已降级为待人工复核",
                    remediation="请人工复核该维度",
                    confidence=0.0,
                    needs_human_review=True,
                )
            )
        db.commit()
        publish_event(str(task_id), "taskStatus", {"status": "done", "progress": 100})
        # M9 集成：降级也生成报告（保证报告永远存在）
        generate_report(db=db, task_id=task_id)


def _mark_failed(task_id: uuid.UUID, error: str) -> None:
    """标记任务失败（降级也失败时的兜底）。"""
    with SessionLocal() as db:
        task = db.get(ReviewTask, task_id)
        if task is not None:
            task.status = "failed"
            task.error = error[:500]
            db.commit()
