"""审查任务（M4-3）：Celery 异步执行 LangGraph 审查工作流。

流程：读 Document → 标记 running → 跑工作流（orchestrator + D1-D6 + 反思 + report）
→ 写 ComplianceFinding → 标记 done。
降级容错（ARCHITECTURE 6.4）：工作流异常/超时 → 标记 failed，并写入一条
"待补 + needsHumanReview=true" 的降级 finding，任务不中断。
"""

import asyncio
import logging
import threading
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

# 进度映射：6 维 + critic 共 7 个节点，10%→90% 线性推进（100% 由完成落库时写入）
_PROGRESS_NODES = 7


def _track_progress(task_id: uuid.UUID, stop: threading.Event) -> None:
    """后台线程：消费 nodeEnd 专用进度队列，按完成节点数更新 DB 进度（10→90）。

    只更新 running 状态的任务；Redis 不可用 / 队列空时轮询等待，stop 置位即退出。
    """
    import time

    from app.core.sse import _redis

    done_dims: set[str] = set()
    while not stop.is_set():
        try:
            client = _redis()
            if client is None:
                return
            item = client.lpop(f"task:{task_id}:progress")
            if not item:
                time.sleep(1.0)
                continue
            if item and item not in done_dims:
                done_dims.add(item)
                progress = min(90, 10 + int(80 * len(done_dims) / _PROGRESS_NODES))
                with SessionLocal() as db:
                    t = db.get(ReviewTask, task_id)
                    if t is not None and t.status == "running":
                        t.progress = progress
                        db.commit()
                        # M10 修复：进度同步发布 taskStatus 事件。此前进度只写 DB
                        # 不发事件，SSE 端会一直卡在任务启动时滞留的 10% 旧事件，
                        # 与任务列表页（REST 读 DB，显示 90%）不同步。
                        publish_event(
                            str(task_id),
                            "taskStatus",
                            {"status": "running", "progress": progress},
                        )
        except Exception:  # noqa: BLE001 — 进度跟踪失败绝不影响审查主流程
            time.sleep(2.0)


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
        # M9-8：按任务归属用户取自有 Key（无 user_id / 用户无 Key → None 走系统 Key）
        api_key_override = None
        if task.user_id is not None:
            from app.models import User
            from app.services.user_api_key_service import get_user_api_key_plain

            owner = db.get(User, task.user_id)
            if owner is not None:
                api_key_override = get_user_api_key_plain(db, owner)
        publish_event(str(task_id), "taskStatus", {"status": "running", "progress": 10})

    # 后台进度跟踪：nodeEnd 事件 → DB 进度（10→90），工作流结束后停止
    stop_tracker = threading.Event()
    tracker = threading.Thread(target=_track_progress, args=(task_id, stop_tracker), daemon=True)
    tracker.start()
    try:
        graph = build_workflow()
        # LangGraph 是 async 图，用 asyncio.run 同步驱动（Celery worker 内）
        state = asyncio.run(
            graph.ainvoke(
                {
                    "task_id": str(task_id),
                    "document_id": str(document_id),
                    "document_text": text,
                    "api_key_override": api_key_override,
                }
            )
        )
    finally:
        stop_tracker.set()
        tracker.join(timeout=3.0)

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
