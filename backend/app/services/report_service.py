"""报告生成服务（M9-1）。

- 查 ReviewTask + findings，summary 自动生成（findingCount + highRiskCount + 简短结论）；
- baselineVersion 从 config.LAWS_BASELINE_VERSION 读（禁止硬编码）；
- findings 按 dimension 分组（d1-d6 + crossConsistency）组织到 content_json；
- crossDocConflicts：联合审查模式由调用方传入（M6 表后续接入）；
- md_export：朴素 markdown 序列化（M9-3 完善）；
- upsert Report（task_id 唯一，重复调用幂等更新）。
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ComplianceFinding, Report, ReviewTask
from app.schemas.report import ReportOut


def _finding_dict(f: ComplianceFinding) -> dict:
    """ComplianceFinding ORM → 契约字段（camelCase）。"""
    return {
        "id": str(f.id),
        "taskId": str(f.task_id),
        "dimension": f.dimension.value,
        "verdict": f.verdict.value,
        "level": f.level.value,
        "clauseRef": f.clause_ref,
        "statuteVersion": f.statute_version,
        "description": f.description,
        "remediation": f.remediation,
        "confidence": f.confidence,
        "needsHumanReview": f.needs_human_review,
        "evidence": None,
    }


def _group_by_dimension(findings: list[ComplianceFinding]) -> dict[str, list[dict]]:
    """findings 按 dimension 分组（d1-d6 + crossConsistency）。"""
    grouped: dict[str, list[dict]] = {}
    for f in findings:
        dim = f.dimension.value
        grouped.setdefault(dim, []).append(_finding_dict(f))
    return grouped


def _generate_summary(findings: list[ComplianceFinding]) -> str:
    """summary 自动生成：findingCount + highRiskCount + 简短结论。"""
    high = sum(1 for f in findings if f.level.value == "high")
    if high > 0:
        conclusion = f"发现 {high} 项高风险项，需重点关注"
    elif findings:
        conclusion = "未发现高风险项，存在一般性合规建议"
    else:
        conclusion = "未产生审查结论"
    return f"共审查 {len(findings)} 项，其中高风险 {high} 项；{conclusion}"


def _build_content(
    *,
    task_id: uuid.UUID,
    findings: list[ComplianceFinding],
    conflicts: list[dict],
) -> dict[str, Any]:
    """组装 Report content_json（契约 4.9）。"""
    summary = _generate_summary(findings)
    high_count = sum(1 for f in findings if f.level.value == "high")
    content = {
        "taskId": str(task_id),
        "summary": summary,
        "baselineVersion": get_settings().laws_baseline_version,
        "generatedAt": None,  # 由 Report.generated_at 落库后回填
        "findingCount": len(findings),
        "highRiskCount": high_count,
        "findings": [_finding_dict(f) for f in findings],
        "findingsByDimension": _group_by_dimension(findings),
        "crossDocConflicts": conflicts,
    }
    return content


def _finding_md(f: dict) -> str:
    """单条 finding 的 markdown（补全 confidence/statuteVersion/needsHumanReview/evidence）。"""
    lines = [f"### [{f.get('dimension', '')}] {f.get('verdict', '')}（{f.get('level', '')}）", ""]
    lines.append(f"- 条款：{f.get('clauseRef', '待补')}")
    lines.append(f"- 法规版本：{f.get('statuteVersion') or '待补'}")
    confidence = f.get("confidence")
    if confidence is not None:
        lines.append(f"- 置信度：{round(float(confidence) * 100)}%")
    if f.get("needsHumanReview"):
        lines.append("- ⚠️ 需人工复核")
    lines.append(f"- 说明：{f.get('description', '')}")
    if f.get("remediation"):
        lines.append(f"- 整改建议：{f.get('remediation', '')}")
    evidence = f.get("evidence") or {}
    if evidence.get("text"):
        lines.append(f"- 证据：{evidence['text']}")
    return "\n".join(lines)


def to_markdown(report: Report) -> str:
    """Markdown 序列化（M9-3 完善）。

    保持与 HTML 报告同源同结构：
    报告头 → 摘要 → 审查发现（按维度分组）→ 跨文档矛盾 → 免责声明。
    每条 finding 含条款引用/法规版本/置信度/需人工复核/证据/整改建议。
    """
    c = report.content_json
    lines = [
        "# 合规审查报告",
        "",
        f"- **任务 ID**：{report.task_id}",
        f"- **法规基线版本**：{report.baseline_version}",
        f"- **生成时间**：{report.generated_at}",
        f"- **发现数**：{c.get('findingCount', 0)}（高风险 {c.get('highRiskCount', 0)}）",
        "",
        "## 摘要",
        "",
        c.get("summary", ""),
        "",
        "## 审查发现",
        "",
    ]

    grouped = c.get("findingsByDimension") or {}
    if grouped:
        for dim, findings in grouped.items():
            lines.append(f"### {dim}（{len(findings)} 项）")
            lines.append("")
            for f in findings:
                lines.append(_finding_md(f))
                lines.append("")
    else:
        for f in c.get("findings", []):
            lines.append(_finding_md(f))
            lines.append("")

    conflicts = c.get("crossDocConflicts") or []
    if conflicts:
        lines.append("## 跨文档矛盾")
        lines.append("")
        for conflict in conflicts:
            lines.append(f"### {conflict.get('declarationKey', '')}（{conflict.get('level', '')}）")
            lines.append("")
            for side, key in (("文档 A", "docA"), ("文档 B", "docB")):
                doc = conflict.get(key) or {}
                lines.append(f"- {side}：{doc.get('value', '待补')}")
                evidence = doc.get("evidence") or {}
                if evidence.get("text"):
                    lines.append(f"  - 证据：{evidence['text']}")
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "> **免责声明**：本报告由 AI 生成，仅供参考，不构成法律意见。",
            "> 高风险项与需人工复核项请由专业法律顾问最终确认。",
        ]
    )
    return "\n".join(lines)


def generate_report(
    *, db: Session, task_id: uuid.UUID, conflicts: list[dict] | None = None
) -> Report:
    """生成/更新报告（task_id 唯一，幂等 upsert）。返回 Report ORM。"""
    task = db.get(ReviewTask, task_id)
    if task is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("任务不存在", code="task_not_found")

    findings = list(
        db.scalars(select(ComplianceFinding).where(ComplianceFinding.task_id == task_id)).all()
    )

    content = _build_content(task_id=task_id, findings=findings, conflicts=conflicts or [])
    baseline = get_settings().laws_baseline_version

    # upsert（task_id 唯一）
    report = db.scalar(select(Report).where(Report.task_id == task_id))
    if report is None:
        report = Report(
            task_id=task_id, content_json=content, md_export="", baseline_version=baseline
        )
        db.add(report)
    else:
        report.content_json = content
        report.baseline_version = baseline

    # 先 commit 让 generated_at 落库，再生成 markdown + 回填 content generatedAt
    db.commit()
    db.refresh(report)
    report.content_json = {**content, "generatedAt": report.generated_at.isoformat()}
    report.md_export = to_markdown(report)
    db.commit()
    db.refresh(report)
    return report


def get_report(db: Session, task_id: uuid.UUID) -> Report | None:
    """查询报告（无则返回 None）。"""
    return db.scalar(select(Report).where(Report.task_id == task_id))


def report_out(report: Report) -> dict:
    """Report ORM → ReportOut 契约（camelCase）。"""
    return ReportOut.model_validate(report.content_json).model_dump(by_alias=True)
