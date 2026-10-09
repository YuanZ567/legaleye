"""LangGraph 审查工作流（M4-3 骨架 + M5 Critic）。

状态流转：orchestrator → 六维并行(D1-D6) → Critic(矛盾检测) → 反思(≤2轮) → report。
- 六节点真实 LLM 经 factory（可注入 mock）；Critic 跨维度矛盾检测 + 高风险复核；
- 反思：基于 Critic 打回的维度重跑，≤2 轮强制结束（ARCHITECTURE 6.4 防死循环）；
- SSE：各节点发布 nodeStart/nodeEnd/taskStatus/tokenUsage。

图使用 async 节点（配合 Celery async 编排），亦可同步 invoke 测试。
"""

import asyncio
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.critic import Critic
from app.agents.dimension_agent import build_dimension_node
from app.core.sse import publish_event

MAX_REFLECTION_ROUNDS = 2
DIMENSIONS = ["d1", "d2", "d3", "d4", "d5", "d6"]


def _merge_findings(left: list[dict], right: list[dict]) -> list[dict]:
    """findings reducer：按 dimension 合并，后到的覆盖先到的（反思重跑覆盖当轮结果）。

    避免并行节点并发写冲突（需 reducer），同时反思轮不累积旧结果。
    """
    merged = {f.get("dimension"): f for f in left}
    for f in right:
        merged[f.get("dimension")] = f
    return list(merged.values())


def _append_dims(left: list[str], right: list[str]) -> list[str]:
    """reconsider_dims reducer：追加去重。"""
    return list(dict.fromkeys(left + right))


class WorkflowState(TypedDict, total=False):
    """工作流共享状态。"""

    task_id: str
    document_id: str
    document_text: str
    retrieval: str
    graph_summary: str
    # M9-8：用户自有 API Key 明文（worker 按 task.user_id 解析后透传；无 → None 走系统 Key）
    api_key_override: str
    # findings 用 reducer 合并：六维并行各自追加 + 反思按 dimension 覆盖
    findings: Annotated[list[dict], _merge_findings]
    reflection_round: int
    # Critic 打回的维度（反思重跑用），列表 reducer
    reconsider_dims: Annotated[list[str], _append_dims]
    # 文档是否声明"不出境"（供 Critic 不出境-图谱出境矛盾检测）
    declares_no_outbound: bool
    # M6 多文档模式：multi 任务传多份原文（Critic 节点调 crossdoc 做跨文档矛盾检测）
    # single 任务保持 None；d1-d6 节点仍走 document_text（拼接文本）
    documents: list[str]


async def _default_llm_func(**kwargs: Any) -> str:
    """默认 LLM 调用（生产）：经 llm/factory.chat_completion，自动记账。

    测试/CI 通过注入 mock 覆盖；真实百炼集成用 ModelConfig + OPENAI_API_KEY。
    """
    from app.core.db import SessionLocal
    from app.core.enums import Provider
    from app.llm.factory import chat_completion

    with SessionLocal() as db:
        chat_kwargs: dict[str, Any] = {
            "db": db,
            "provider": Provider.BAILIAN,
            "model": None,
            "messages": kwargs["messages"],
            "node": kwargs.get("dimension"),
            "task_id": kwargs.get("task_id"),
        }
        # M9-8：有用户自有 Key 则透传（否则走系统 Key）
        if kwargs.get("api_key_override"):
            chat_kwargs["api_key_override"] = kwargs["api_key_override"]
        return await asyncio.to_thread(chat_completion, **chat_kwargs)


def _build_agent(dimension: str, llm_func: Any | None):
    """构建六维节点（真实 LLM 经 factory，可注入 mock）。"""
    fn = llm_func or _default_llm_func
    return build_dimension_node(dimension, fn)


def _orchestrator(state: WorkflowState) -> dict:
    """编排节点：准备检索与图谱摘要，分发给六维节点。

    反思重跑时重置 findings（每轮只保留当轮六维结果，避免 reducer 累积）。
    检索/图谱失败降级为空占位（不中断）。
    """
    publish_event(state["task_id"], "taskStatus", {"status": "running", "progress": 10})
    document_id = state.get("document_id", "")
    retrieval = state.get("retrieval")
    graph_summary = state.get("graph_summary")
    if retrieval is None or graph_summary is None:
        # 首轮：执行法条检索（多 query 覆盖跨境/收集/同意等）+ 图谱查询（失败降级）
        from app.agents.tools import query_dataflow_graph, retrieve_law_multi
        from app.core.db import SessionLocal

        with SessionLocal() as db:
            retrieval = retrieve_law_multi(
                db,
                [
                    "个人信息跨境向境外提供的条件与单独同意义务",
                    "个人信息收集的最小必要与合法正当",
                    "向第三方提供个人信息与单独同意",
                    "委托处理第三方与告知同意",
                    "数据主体查询复制更正删除权利",
                    "处理个人信息的合法性基础与告知义务",
                    "数据出境安全评估的条件",
                ],
                top_k=3,
            )
            graph_summary = query_dataflow_graph(db, document_id) if document_id else ""
    return {
        "retrieval": retrieval,
        "graph_summary": graph_summary,
        "findings": [],
    }


def _needs_reflection(state: WorkflowState) -> str:
    """反思路由：Critic 打回维度非空 或 含待补，且轮次<2 → 再一轮；否则结束。

    轮次上限 MAX_REFLECTION_ROUNDS 强制结束（ARCHITECTURE 6.4 防死循环）。
    """
    round_no = state.get("reflection_round", 0)
    findings = state.get("findings", [])
    reconsidered = state.get("reconsider_dims", [])
    # has_pending：待补/需人工复核才触发再试一轮。notApplicable 属于确定性结论
    # （含 M10 证据锚定降级——模型报违规但证据在文档中找不到 → 判不适用），
    # 其 clauseRef 为空是正常形态，不应触发反思（2026-09-04：否则幻觉维度
    # 每份文档白跑 2 轮反思 × 6 次 LLM 调用，4.5-flash 慢请求时间成本爆炸）。
    has_pending = any(
        (f.get("clauseRef") in ("", "待补") or f.get("needsHumanReview"))
        and f.get("verdict") != "notApplicable"
        for f in findings
    )
    if (reconsidered or has_pending) and round_no < MAX_REFLECTION_ROUNDS:
        return "agents"
    return "report"


def _reflect(state: WorkflowState) -> dict:
    """反思节点：递增轮次（仅路由计数；打回维度在 Critic 已产出）。"""
    publish_event(state["task_id"], "taskStatus", {"status": "running", "progress": 60})
    return {"reflection_round": state.get("reflection_round", 0) + 1}


def _critic(state: WorkflowState) -> dict:
    """Critic 节点（后置）：矛盾检测 + 高风险复核，产出 crossConsistency 与打回维度。

    多文档场景（M6）：调 crossdoc 服务做跨文档声明键对比，检出矛盾追加 crossConsistency finding。
    """
    critic = Critic(document_declares_no_outbound=state.get("declares_no_outbound", False))
    new_findings, reconsider_dims = critic.analyze(
        task_id=state["task_id"],
        findings=state.get("findings", []),
        graph_summary=state.get("graph_summary", ""),
    )
    # M6：multi 文档场景接入 crossdoc 规则做确定性矛盾检测
    documents = state.get("documents") or []
    if len(documents) >= 2:
        from app.core.enums import DeclarationKey
        from app.services.crossdoc import (
            declaration_sets_conflict,
            extract_declaration_sets,
        )

        sets_a = extract_declaration_sets(documents[0])
        sets_b = extract_declaration_sets(documents[1])
        for key in DeclarationKey:
            a_hits, b_hits = sets_a.get(key), sets_b.get(key)
            if not a_hits or not b_hits:
                continue
            if declaration_sets_conflict(a_hits, b_hits):
                new_findings.append(
                    {
                        "dimension": "crossConsistency",
                        "verdict": "nonCompliant",
                        "level": "high",
                        "clauseRef": "",
                        "statuteVersion": None,
                        "description": f"跨文档声明矛盾: {key.value}",
                        "remediation": "统一两份文档的相关声明",
                        "confidence": 0.9,
                        "needsHumanReview": False,
                    }
                )
    return {
        "findings": new_findings,
        "reconsider_dims": reconsider_dims,
    }


def _report(state: WorkflowState) -> dict:
    """报告节点：汇总 findings（骨架，M4-5 生成正式报告）。"""
    publish_event(
        state["task_id"],
        "taskStatus",
        {"status": "done", "progress": 100, "findingCount": len(state.get("findings", []))},
    )
    return {"findings": state.get("findings", [])}


def build_workflow(agent_fns: dict[str, Any] | None = None) -> StateGraph:
    """构建 LangGraph 工作流。

    :param agent_fns: 维度 → LLM 函数（测试注入 mock LLM；默认走 factory 真实调用）。
    """
    g = StateGraph(WorkflowState)
    g.add_node("orchestrator", _orchestrator)
    for dim in DIMENSIONS:
        fn = _build_agent(dim, (agent_fns or {}).get(dim))
        g.add_node(dim, fn)
    g.add_node("critic", _critic)
    g.add_node("reflect", _reflect)
    g.add_node("report", _report)

    g.add_edge(START, "orchestrator")
    # 六维并行 → Critic（后置矛盾检测）
    for dim in DIMENSIONS:
        g.add_edge("orchestrator", dim)
        g.add_edge(dim, "critic")
    g.add_edge("critic", "reflect")
    # 反思路由
    g.add_conditional_edges(
        "reflect", _needs_reflection, {"agents": "orchestrator", "report": "report"}
    )
    g.add_edge("report", END)
    return g.compile()
