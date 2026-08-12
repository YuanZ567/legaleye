"""图谱服务（M3-5）：从 Document 文本构建图谱并执行 R1-R4 推理。

流程：Document.raw_text → 规则抽取（M3-2）→ 建图（M3-1）→ R1-R4（M3-4）
→ 序列化为契约 GraphPayload（含 riskPaths/suggestions）。

LLM 抽取通道（M3-3）真实接入等 M4；当前规则通道确定性可复现。
"""

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.enums import PathType, RiskLevel
from app.graph.builder import GraphBuilder
from app.graph.reasoning import Reasoner
from app.graph.rule_extractor import extract_by_rules
from app.models import Document
from app.schemas.graph import GraphPayload, RiskPath, Suggestion


def build_graph_for_document(
    *,
    db: Session,
    document_id: uuid.UUID,
    declares_no_outbound: bool = False,
) -> GraphPayload:
    """为指定 Document 构建图谱并推理（文档不存在抛 404）。"""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    text = doc.raw_text or ""
    extraction = extract_by_rules(text)

    builder = GraphBuilder()
    builder.build(extraction.entities, extraction.edges)
    reasoner = Reasoner(builder.graph, declares_no_outbound=declares_no_outbound)

    payload = builder.to_payload()
    payload.risk_paths = _build_risk_paths(reasoner)
    payload.suggestions = _build_suggestions(reasoner)
    return payload


def _build_risk_paths(reasoner: Reasoner) -> list[RiskPath]:
    """聚合 R1/R2/R3 的风险路径为契约 riskPaths。"""
    records = (
        reasoner.reachable_outbound_paths()
        + reasoner.unauthorized_cross_border_edges()
        + reasoner.declaration_conflict()
    )
    seen: set[tuple[str, ...]] = set()
    paths: list[RiskPath] = []
    for r in records:
        key = tuple(r.path)
        if key in seen:
            continue
        seen.add(key)
        paths.append(
            RiskPath(
                path=r.path,
                edges=r.edge_ids,
                reason=r.reason,
                level=r.level,
            )
        )
    return paths


def _build_suggestions(reasoner: Reasoner) -> list[Suggestion]:
    """聚合 R4 建议为契约 suggestions。"""
    risks = (
        reasoner.unauthorized_cross_border_edges()
        + reasoner.reachable_outbound_paths()
        + reasoner.declaration_conflict()
    )
    raw = reasoner.suggestions(risks)
    return [
        Suggestion(
            path_type=PathType(s["pathType"]),
            advice=s["advice"],
            level=RiskLevel(s["level"]),
        )
        for s in raw
    ]
