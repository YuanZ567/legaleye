"""审查工具集（M4-4）：D1-D6 节点可调用的检索/图谱工具。

- retrieve_law_baseline(query)：语义检索法条基线（Top-3），无命中返回空（不编造）；
- query_dataflow_graph(document_id)：查询数据流图谱风险路径（跨境等）；
- compare_scc_template(...)：SCC 模板比对（骨架，M4-6 完善）。
"""

import logging

from sqlalchemy.orm import Session

from app.knowledge.retrieval import semantic_search

logger = logging.getLogger(__name__)


def retrieve_law_baseline(db: Session, query: str, top_k: int = 3) -> str:
    """语义检索相关法条，返回可读文本（供 LLM 依据；无命中返回"待补"提示）。"""
    try:
        hits = semantic_search(db=db, query=query, top_k=top_k)
    except Exception as exc:  # embedding 未配置/失败时不阻塞
        logger.warning("法条检索失败: %s", exc)
        return "（法条检索不可用）"
    if not hits:
        return "（无相关法条命中）"
    lines = []
    for h in hits:
        lines.append(f"[{h.clause_ref} · {h.statute_version}] {h.article_text}")
    return "\n".join(lines)


def retrieve_law_multi(db: Session, queries: list[str], top_k: int = 3) -> str:
    """多 query 语义检索合并去重（确保覆盖跨境/收集/同意等各维度条款）。

    供 orchestrator 使用：合并结果按法条去重，保证 D5 等维度能在检索结果中
    找到对应条款号（满足"clauseRef 必须命中检索结果"的红线校验）。
    """
    seen: set[str] = set()
    lines: list[str] = []
    for q in queries:
        try:
            hits = semantic_search(db=db, query=q, top_k=top_k)
        except Exception as exc:  # embedding 失败不阻塞
            logger.warning("法条检索失败(%s): %s", q, exc)
            continue
        for h in hits:
            key = (h.clause_ref, h.statute_version)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"[{h.clause_ref} · {h.statute_version}] {h.article_text}")
    if not lines:
        return "（无相关法条命中）"
    return "\n".join(lines)


def query_dataflow_graph(db: Session, document_id: str) -> str:
    """查询数据流图谱风险路径（返回跨境等风险摘要，供 D5 使用）。"""
    from app.services.graph_service import build_graph_for_document

    try:
        payload = build_graph_for_document(db=db, document_id=document_id)
    except Exception as exc:
        logger.warning("图谱查询失败: %s", exc)
        return "（图谱不可用）"
    risks = payload.risk_paths
    if not risks:
        return "（无出境风险路径）"
    return "\n".join(f"· {r.path} → {r.level}: {r.reason}" for r in risks)
