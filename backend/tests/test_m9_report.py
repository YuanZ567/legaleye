"""M9-1 验收测试：报告生成 + API。

- 生成报告成功 → 字段齐全（summary/baselineVersion/findingCount/highRiskCount/findings）；
- high_risk_count 统计正确；
- findings 按 dimension 分组（d1-d6 + crossConsistency）；
- 联合审查模式 crossDocConflicts 带入；
- baselineVersion 锁定 config 常量；
- 重复生成幂等（task_id 唯一不报错）；
- 鉴权：归属校验（他人报告 403）。
"""

import uuid
from collections.abc import Generator

import pytest
from app.core.db import get_db
from app.core.enums import FindingLevel, FindingVerdict, ReviewDimension
from app.main import create_app
from app.models import SQLModel
from app.models.review_task import ComplianceFinding
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client(monkeypatch) -> Generator[tuple[TestClient, sessionmaker], None, None]:
    from app.services import rate_limit_service

    monkeypatch.setattr(rate_limit_service, "check_demo_limit", lambda **kw: None)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSession() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c, TestingSession
    SQLModel.metadata.drop_all(engine)


def _register_user(client: TestClient, email="u@x.com") -> tuple[str, str]:
    """注册用户，返回 (token, user_id)。"""
    resp = client.post("/auth/register", json={"email": email, "password": "secret123"})
    data = resp.json()["data"]
    return data["token"], data["user"]["id"]


def _seed_task_and_findings(
    client: TestClient, TestingSession, token: str, user_id: str
) -> uuid.UUID:
    """创建任务 + 写 3 条 finding（含 2 条 high），返回 task_id。"""
    import app.api.tasks as tasks_api

    original = tasks_api.dispatch_task
    tasks_api.dispatch_task = lambda task_id, document_id: None
    try:
        resp = client.post(
            "/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json={"documentIds": [str(uuid.uuid4())]},
        )
    finally:
        tasks_api.dispatch_task = original
    task_id = resp.json()["taskId"]

    with TestingSession() as s:
        s.add(
            ComplianceFinding(
                task_id=uuid.UUID(task_id),
                dimension=ReviewDimension.D1_COLLECTION,
                verdict=FindingVerdict.NON_COMPLIANT,
                level=FindingLevel.HIGH,
                clause_ref="第五条",
                description="收集范围超出最小必要",
                remediation="缩减",
                confidence=0.9,
            )
        )
        s.add(
            ComplianceFinding(
                task_id=uuid.UUID(task_id),
                dimension=ReviewDimension.D5_CROSS_BORDER,
                verdict=FindingVerdict.COMPLIANT,
                level=FindingLevel.LOW,
                clause_ref="第三十九条",
                description="已取得单独同意",
                remediation="",
                confidence=0.8,
            )
        )
        s.add(
            ComplianceFinding(
                task_id=uuid.UUID(task_id),
                dimension=ReviewDimension.CROSS_CONSISTENCY,
                verdict=FindingVerdict.NON_COMPLIANT,
                level=FindingLevel.HIGH,
                clause_ref="待补",
                description="声明与行为矛盾",
                remediation="复核",
                confidence=0.0,
                needs_human_review=True,
            )
        )
        s.commit()
    return uuid.UUID(task_id)


def _generate(TestingSession, task_id: str) -> dict:
    """用测试内存库生成报告。"""
    from app.services.report_service import generate_report, report_out

    with TestingSession() as db:
        report = generate_report(db=db, task_id=uuid.UUID(task_id))
        return report_out(report)


def test_generate_report_fields_complete(client):
    """生成报告成功 → 字段齐全。"""
    c, ts = client
    token, user_id = _register_user(c)
    task_id = _seed_task_and_findings(c, ts, token, user_id)
    report = _generate(ts, str(task_id))

    assert report["findingCount"] == 3
    assert report["highRiskCount"] == 2
    assert report["summary"]
    assert "baselineVersion" in report
    assert "generatedAt" in report
    assert len(report["findings"]) == 3


def test_high_risk_count_correct(client):
    """high_risk_count 统计正确（2 条 high）。"""
    c, ts = client
    token, user_id = _register_user(c)
    task_id = _seed_task_and_findings(c, ts, token, user_id)
    report = _generate(ts, str(task_id))
    assert report["highRiskCount"] == 2


def test_findings_grouped_by_dimension(client):
    """findings 按 dimension 分组（d1-d6 + crossConsistency）。"""
    from app.services.report_service import generate_report

    c, ts = client
    token, user_id = _register_user(c)
    task_id = _seed_task_and_findings(c, ts, token, user_id)
    with ts() as db:
        report = generate_report(db=db, task_id=task_id)
    grouped = report.content_json["findingsByDimension"]
    assert "d1Collection" in grouped
    assert "d5CrossBorder" in grouped
    assert "crossConsistency" in grouped
    assert len(grouped["d1Collection"]) == 1


def test_cross_doc_conflicts_included(client):
    """联合审查模式 crossDocConflicts 带入。"""
    from app.services.report_service import generate_report

    c, ts = client
    token, user_id = _register_user(c)
    task_id = _seed_task_and_findings(c, ts, token, user_id)
    conflicts = [
        {
            "id": str(uuid.uuid4()),
            "declarationKey": "crossBorder",
            "docA": {"documentId": str(uuid.uuid4()), "value": "不出境", "evidence": {"text": "x"}},
            "docB": {"documentId": str(uuid.uuid4()), "value": "向境外", "evidence": {"text": "y"}},
            "level": "high",
        }
    ]
    with ts() as db:
        report = generate_report(db=db, task_id=task_id, conflicts=conflicts)
    assert len(report.content_json["crossDocConflicts"]) == 1
    assert report.content_json["crossDocConflicts"][0]["declarationKey"] == "crossBorder"


def test_baseline_version_locked(client):
    """baseline_version 锁定 config 常量。"""
    from app.core.config import get_settings
    from app.services.report_service import generate_report

    c, ts = client
    token, user_id = _register_user(c)
    task_id = _seed_task_and_findings(c, ts, token, user_id)
    with ts() as db:
        report = generate_report(db=db, task_id=task_id)
    assert report.baseline_version == get_settings().laws_baseline_version


def test_idempotent_regenerate(client):
    """重复生成幂等（task_id 唯一，不报错，报告数 1）。"""
    from app.models import Report
    from app.services.report_service import generate_report

    c, ts = client
    token, user_id = _register_user(c)
    task_id = _seed_task_and_findings(c, ts, token, user_id)
    with ts() as db:
        generate_report(db=db, task_id=task_id)
        generate_report(db=db, task_id=task_id)  # 幂等
        count = db.query(Report).filter(Report.task_id == task_id).count()
    assert count == 1


def test_to_markdown_contains_all_fields(client):
    """to_markdown 包含 4 个新字段 + 免责声明 + 矛盾区详情。"""
    from types import SimpleNamespace

    from app.services.report_service import to_markdown

    content = {
        "summary": "共审查 1 项，其中高风险 1 项；发现 1 项高风险项，需重点关注",
        "findingCount": 1,
        "highRiskCount": 1,
        "findings": [
            {
                "id": str(uuid.uuid4()),
                "dimension": "d1Collection",
                "verdict": "nonCompliant",
                "level": "high",
                "clauseRef": "第五条",
                "statuteVersion": "个人信息保护法(2021)",
                "description": "收集范围超出最小必要。",
                "remediation": "缩减至最小必要字段。",
                "confidence": 0.87,
                "needsHumanReview": True,
                "evidence": {"text": "收集手机号、定位等非必要信息", "charRange": [10, 20]},
            }
        ],
        "findingsByDimension": {
            "d1Collection": [
                {
                    "id": str(uuid.uuid4()),
                    "dimension": "d1Collection",
                    "verdict": "nonCompliant",
                    "level": "high",
                    "clauseRef": "第五条",
                    "statuteVersion": "个人信息保护法(2021)",
                    "description": "收集范围超出最小必要。",
                    "remediation": "缩减至最小必要字段。",
                    "confidence": 0.87,
                    "needsHumanReview": True,
                    "evidence": {"text": "收集手机号、定位等非必要信息", "charRange": [10, 20]},
                }
            ]
        },
        "crossDocConflicts": [
            {
                "id": str(uuid.uuid4()),
                "declarationKey": "crossBorder",
                "docA": {
                    "documentId": str(uuid.uuid4()),
                    "value": "不出境",
                    "evidence": {"text": "政策未提及出境"},
                },
                "docB": {
                    "documentId": str(uuid.uuid4()),
                    "value": "向境外",
                    "evidence": {"text": "DPA 列出境外接收方"},
                },
                "level": "high",
            }
        ],
    }
    report = SimpleNamespace(
        task_id=uuid.uuid4(),
        baseline_version="laws-v1.0-20260811",
        generated_at="2026-08-14T00:00:00Z",
        content_json=content,
    )
    md = to_markdown(report)

    # 4 个新字段
    assert "条款：第五条" in md
    assert "法规版本：个人信息保护法(2021)" in md
    assert "置信度：87%" in md
    assert "⚠️ 需人工复核" in md
    assert "证据：收集手机号、定位等非必要信息" in md
    # 矛盾区详情
    assert "跨文档矛盾" in md
    assert "文档 A：不出境" in md
    assert "文档 B：向境外" in md
    assert "DPA 列出境外接收方" in md
    # 免责声明
    assert "免责声明" in md
    assert "仅供参考，不构成法律意见" in md
    # 与 HTML 报告同源同结构：按维度分组章节
    assert "## 摘要" in md
    assert "## 审查发现" in md
