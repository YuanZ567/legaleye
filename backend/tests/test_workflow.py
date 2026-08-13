"""M4-3 验收测试：LangGraph 审查工作流骨架。

- 状态流转：orchestrator → 六维并行 → 反思 → report；
- SSE 事件发布：nodeStart/nodeEnd/taskStatus 被发布；
- 反思循环 ≤2 轮：待补 finding 触发反思，轮次不超过 2；
- 无待补 → 直接 report，不反思。

测试用默认 mock 节点 + monkeypatch SSE 发布（不连真实 Redis）。
"""

import asyncio
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
    c = EventCollector()
    monkeypatch.setattr(workflow, "publish_event", c.publish)
    yield c


def _base_state(**overrides):
    state = {
        "task_id": "task-1",
        "document_id": "doc-1",
        "document_text": "文档原文",
    }
    state.update(overrides)
    return state


def test_workflow_produces_six_findings():
    """工作流执行后产出 6 条 finding（六维）。"""
    graph = build_workflow()
    result = asyncio.run(graph.ainvoke(_base_state()))
    findings = result.get("findings", [])
    assert len(findings) == 6
    dims = {f["dimension"] for f in findings}
    assert dims == {"d1", "d2", "d3", "d4", "d5", "d6"}


def test_workflow_emits_sse_events(collector):
    """SSE 事件发布：nodeStart/nodeEnd/taskStatus 均被发布。"""
    graph = build_workflow()
    asyncio.run(graph.ainvoke(_base_state()))

    types = [e[1] for e in collector.events]
    assert "nodeStart" in types
    assert "nodeEnd" in types
    assert "taskStatus" in types
    # 至少首轮六维节点发布了 nodeStart（默认 mock 全待补 → 反思重跑 → ≥6）
    node_starts = [e for e in collector.events if e[1] == "nodeStart"]
    assert len(node_starts) >= 6


def test_reflection_runs_until_no_pending():
    """反思循环：待补 finding 触发反思，最多 2 轮。"""
    # 注入可计数的 agent：始终返回待补（触发反思）
    calls = {"d1": 0}

    async def pending_agent(state):
        calls["d1"] += 1
        return {"findings": [{"dimension": "d1", "clauseRef": "待补", "needsHumanReview": True}]}

    g = build_workflow({"d1": pending_agent})
    asyncio.run(g.ainvoke(_base_state()))
    # d1 被调用次数 = 初轮 + 反思轮（最多 2 轮反思）
    assert calls["d1"] <= 1 + workflow.MAX_REFLECTION_ROUNDS


def test_no_pending_skips_reflection():
    """所有 finding 无待补 → 不反思重跑（findings 保持每维一条且非待补）。"""

    def make_clean(dim):
        async def agent(state):
            return {
                "findings": [{"dimension": dim, "clauseRef": "第一条", "needsHumanReview": False}]
            }

        return agent

    g = build_workflow({dim: make_clean(dim) for dim in ["d1", "d2", "d3", "d4", "d5", "d6"]})
    result = asyncio.run(g.ainvoke(_base_state()))
    # 六维结果齐全且无待补（clauseRef 非空、无 needsHumanReview）
    findings = result["findings"]
    assert len(findings) == 6
    assert all(f["clauseRef"] not in ("", "待补") and not f["needsHumanReview"] for f in findings)
