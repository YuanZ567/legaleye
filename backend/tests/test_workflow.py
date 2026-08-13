"""M4-4 验收测试：LangGraph 工作流（六维真实节点经 mock LLM）。

- 状态流转：orchestrator → 六维并行 → 反思 → report；
- SSE 事件：nodeStart/nodeEnd/taskStatus 被发布；
- 反思循环 ≤2 轮（待补触发反思）；
- 无待补不反思。

mock LLM 函数注入（维度→async LLM 返回 JSON 字符串）；state 携带 retrieval 避免连 DB。
"""

import asyncio
import json
from collections.abc import Generator

import pytest
from app.agents import workflow
from app.agents.workflow import build_workflow


class EventCollector:
    """收集 SSE 发布调用。"""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict]] = []

    def publish(self, task_id, event_type, data):
        self.events.append((task_id, event_type, data))


@pytest.fixture()
def collector(monkeypatch) -> Generator[EventCollector, None, None]:
    """monkeypatch 各模块的 publish_event，避免连真实 Redis。"""
    from app.agents import dimension_agent

    c = EventCollector()
    monkeypatch.setattr(workflow, "publish_event", c.publish)
    monkeypatch.setattr(dimension_agent, "publish_event", c.publish)
    yield c


def _base_state(**overrides):
    state = {
        "task_id": "task-1",
        "document_id": "",
        "document_text": "文档原文",
        "retrieval": "（检索结果）",
        "graph_summary": "",
    }
    state.update(overrides)
    return state


# 维度 → 契约值（ReviewDimension）
_DIM_CONTRACT = {
    "d1": "d1Collection",
    "d2": "d2Notice",
    "d3": "d3Purpose",
    "d4": "d4ThirdParty",
    "d5": "d5CrossBorder",
    "d6": "d6DataRights",
}


def _finding_json(dimension: str, clause_ref: str = "第一条", needs_human: bool = False) -> str:
    """构造合法 finding JSON（mock LLM 返回，dimension 用契约值）。"""
    return json.dumps(
        {
            "dimension": _DIM_CONTRACT.get(dimension, dimension),
            "verdict": "nonCompliant" if not needs_human else "unclear",
            "level": "medium",
            "clauseRef": clause_ref,
            "description": f"{dimension} 审查说明",
            "remediation": "整改建议",
            "confidence": 0.8,
            "needsHumanReview": needs_human,
        },
        ensure_ascii=False,
    )


def _make_llm(dimension: str):
    """构造返回该维度合法 finding 的 mock LLM。"""

    async def llm(**kwargs):
        return _finding_json(dimension)

    return llm


def test_workflow_produces_six_findings():
    """工作流执行后产出 6 条 finding（六维）。"""
    agent_fns = {dim: _make_llm(dim) for dim in workflow.DIMENSIONS}
    graph = build_workflow(agent_fns)
    result = asyncio.run(graph.ainvoke(_base_state()))
    findings = result.get("findings", [])
    assert len(findings) == 6
    dims = {f["dimension"] for f in findings}
    assert dims == {
        "d1Collection",
        "d2Notice",
        "d3Purpose",
        "d4ThirdParty",
        "d5CrossBorder",
        "d6DataRights",
    }


def test_workflow_emits_sse_events(collector):
    """SSE 事件发布：nodeStart/nodeEnd/taskStatus 均被发布。"""
    agent_fns = {dim: _make_llm(dim) for dim in workflow.DIMENSIONS}
    graph = build_workflow(agent_fns)
    asyncio.run(graph.ainvoke(_base_state()))

    types = [e[1] for e in collector.events]
    assert "nodeStart" in types
    assert "nodeEnd" in types
    assert "taskStatus" in types
    node_starts = [e for e in collector.events if e[1] == "nodeStart"]
    assert len(node_starts) >= 6


def test_reflection_runs_until_no_pending():
    """反思循环：待补 finding 触发反思，最多 2 轮。"""
    calls = {"d1": 0}

    async def pending_llm(**kwargs):
        calls["d1"] += 1
        return _finding_json("d1", clause_ref="待补", needs_human=True)

    agent_fns = {dim: _make_llm(dim) for dim in workflow.DIMENSIONS}
    agent_fns["d1"] = pending_llm
    g = build_workflow(agent_fns)
    asyncio.run(g.ainvoke(_base_state()))
    assert calls["d1"] <= 1 + workflow.MAX_REFLECTION_ROUNDS


def test_no_pending_skips_reflection():
    """所有 finding 无待补 → 不反思重跑。"""
    agent_fns = {dim: _make_llm(dim) for dim in workflow.DIMENSIONS}
    g = build_workflow(agent_fns)
    result = asyncio.run(g.ainvoke(_base_state()))
    findings = result["findings"]
    assert len(findings) == 6
    assert all(f["clauseRef"] not in ("", "待补") for f in findings)
