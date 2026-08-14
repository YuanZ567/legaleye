"""M9 报告自动生成集成测试（review_task 任务完成后自动生成报告）。

验证 `_run_workflow` 完成后，会调用 report_service.generate_report：
- findings 落库后，Report 自动生成（一任务一报告，task_id 唯一）；
- 不破坏任务状态机（done）。

mock：SessionLocal（内存 SQLite）+ build_workflow（假 async 图）+ publish_event（不连 Redis）。
"""

import uuid
from collections.abc import Generator

import pytest
from app.core.enums import DocType
from app.models import ComplianceFinding, Document, Report, ReviewTask, SQLModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class FakeGraph:
    """假 async 图：返回固定 findings。"""

    async def ainvoke(self, state):
        return {
            "findings": [
                {
                    "dimension": "d1Collection",
                    "verdict": "nonCompliant",
                    "level": "high",
                    "clauseRef": "第五条",
                    "statuteVersion": "个人信息保护法(2021)",
                    "description": "收集范围超出最小必要",
                    "remediation": "缩减",
                    "confidence": 0.9,
                    "needsHumanReview": False,
                }
            ]
        }


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict]] = []

    def publish(self, task_id, event_type, data):
        self.events.append((task_id, event_type, data))


@pytest.fixture()
def env(monkeypatch) -> Generator[tuple[sessionmaker, EventCollector], None, None]:
    """内存 DB + mock build_workflow / publish_event。"""
    import app.tasks.review_task as rt

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    monkeypatch.setattr(rt, "SessionLocal", TestingSession)
    monkeypatch.setattr(rt, "build_workflow", lambda: FakeGraph())
    collector = EventCollector()
    monkeypatch.setattr(rt, "publish_event", collector.publish)
    yield TestingSession, collector
    SQLModel.metadata.drop_all(engine)


def _seed_doc(TestingSession) -> uuid.UUID:
    with TestingSession() as db:
        doc = Document(
            filename="demo.pdf",
            doc_type=DocType.PRIVACY_POLICY,
            char_count=10,
            raw_text="文档原文",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc.id


def test_run_workflow_auto_generates_report(env):
    """任务完成后自动生成报告（findings 落库 + Report 唯一存在）。"""
    from app.tasks.review_task import _run_workflow

    TestingSession, _ = env
    doc_id = _seed_doc(TestingSession)
    task_id = uuid.uuid4()

    _run_workflow(task_id=task_id, document_id=doc_id)

    with TestingSession() as db:
        # findings 已落库
        findings = list(
            db.query(ComplianceFinding).filter(ComplianceFinding.task_id == task_id).all()
        )
        assert len(findings) == 1
        assert findings[0].clause_ref == "第五条"
        # 任务状态 done
        task = db.get(ReviewTask, task_id)
        assert task is not None
        assert task.status == "done"
        # Report 自动生成且唯一
        reports = db.query(Report).filter(Report.task_id == task_id).all()
        assert len(reports) == 1
        assert reports[0].content_json["findingCount"] == 1


def test_run_workflow_report_idempotent(env):
    """报告生成幂等：任务重复完成不产生重复报告。"""
    from app.tasks.review_task import _run_workflow

    TestingSession, _ = env
    doc_id = _seed_doc(TestingSession)
    task_id = uuid.uuid4()

    _run_workflow(task_id=task_id, document_id=doc_id)
    _run_workflow(task_id=task_id, document_id=doc_id)  # 再次运行（模拟重试）

    with TestingSession() as db:
        reports = db.query(Report).filter(Report.task_id == task_id).all()
        assert len(reports) == 1  # upsert，不重复
