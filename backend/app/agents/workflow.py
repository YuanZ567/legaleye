"""LangGraph 审查工作流（M4-3 骨架）。

状态流转：orchestrator → 六维并行(D1-D6) → 反思(≤2轮) → report。
- 六节点默认 mock（骨架验证状态流转/SSE/反思循环），真实 LLM 在 M4-4 接入；
- 反思：若 finding 含"待补"/needsHumanReview 且轮次<2，重跑六节点，否则结束；
- SSE：各节点发布 nodeStart/nodeEnd/taskStatus/tokenUsage。

图使用 async 节点（配合 Celery async 编排），亦可同步 invoke 测试。
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.sse import publish_event
from app.prompts import get_prompt

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


class WorkflowState(TypedDict, total=False):
    """工作流共享状态。"""

    task_id: str
    document_id: str
    document_text: str
    retrieval: str
    graph_summary: str
    # findings 用 reducer 合并：六维并行各自追加 + 反思按 dimension 覆盖
    findings: Annotated[list[dict], _merge_findings]
    reflection_round: int


def _make_default_agent(dimension: str):
    """默认 mock 审查节点（M4-3 骨架；真实 LLM 在 M4-4 替换）。

    依据 prompts 的维度定义生成一个 placeholder finding。
    """

    async def agent(state: WorkflowState) -> dict:
        spec = get_prompt(dimension)
        publish_event(state["task_id"], "nodeStart", {"node": spec.name, "dimension": dimension})
        # 骨架：生成一条占位 finding（M4-4 替换为真实 LLM 调用 + validators）
        finding = {
            "dimension": dimension,
            "verdict": "unclear",
            "level": "medium",
            "clauseRef": "待补",
            "description": f"{spec.name} 审查结果（骨架占位）",
            "remediation": "",
            "confidence": 0.0,
            "needsHumanReview": True,
        }
        publish_event(state["task_id"], "nodeEnd", {"node": spec.name, "dimension": dimension})
        # reducer(add) 会拼接，节点只返回本节点新增的 finding
        return {"findings": [finding]}

    return agent


def _orchestrator(state: WorkflowState) -> dict:
    """编排节点：准备检索与图谱摘要（M4-3 骨架）。

    反思重跑时重置 findings（每轮只保留当轮六维结果，避免 reducer 累积）。
    """
    publish_event(state["task_id"], "taskStatus", {"status": "running", "progress": 10})
    return {
        "retrieval": state.get("retrieval", "（检索结果，M4-3 骨架为空）"),
        "graph_summary": state.get("graph_summary", ""),
        "findings": [],
    }


def _needs_reflection(state: WorkflowState) -> str:
    """反思路由：含待补/低置信且轮次<2 → 再一轮；否则结束。"""
    round_no = state.get("reflection_round", 0)
    findings = state.get("findings", [])
    has_pending = any(
        f.get("clauseRef") in ("", "待补") or f.get("needsHumanReview") for f in findings
    )
    if has_pending and round_no < MAX_REFLECTION_ROUNDS:
        return "agents"
    return "report"


def _reflect(state: WorkflowState) -> dict:
    """反思节点：递增轮次（骨架）。"""
    publish_event(state["task_id"], "taskStatus", {"status": "running", "progress": 60})
    return {"reflection_round": state.get("reflection_round", 0) + 1}


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

    :param agent_fns: 覆盖六节点（测试注入 mock；默认用骨架 mock）。
    """
    g = StateGraph(WorkflowState)
    g.add_node("orchestrator", _orchestrator)
    for dim in DIMENSIONS:
        fn = (agent_fns or {}).get(dim, _make_default_agent(dim))
        g.add_node(dim, fn)
    g.add_node("reflect", _reflect)
    g.add_node("report", _report)

    g.add_edge(START, "orchestrator")
    # 六维并行
    for dim in DIMENSIONS:
        g.add_edge("orchestrator", dim)
        g.add_edge(dim, "reflect")
    # 反思路由
    g.add_conditional_edges(
        "reflect", _needs_reflection, {"agents": "orchestrator", "report": "report"}
    )
    g.add_edge("report", END)
    return g.compile()
