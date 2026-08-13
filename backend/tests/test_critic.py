"""M5-1/M5-2/M5-3 验收测试：Critic 矛盾检测 + 高风险复核 + 反思循环。

- 不出境-图谱出境矛盾（声明不出境 + 图谱含出境路径）；
- 声明-行为矛盾（跨境不合规 + 图谱有出境）；
- 高风险结论复核（needsHumanReview 联动）；
- 无矛盾不产出 crossConsistency finding；
- 反思循环：Critic 打回维度重跑，≤2 轮强制结束。
"""

import asyncio

from app.agents.critic import Critic
from app.agents.workflow import build_workflow


def test_critic_detects_no_outbound_conflict():
    """声明不出境 + 图谱有出境路径 → 检测矛盾，打回 d5。"""
    critic = Critic(document_declares_no_outbound=True)
    findings, dims = critic.analyze(
        task_id="t",
        findings=[{"dimension": "d5CrossBorder", "verdict": "compliant", "level": "low"}],
        graph_summary="检测到跨境出境路径，风险高",
    )
    # 产出 crossConsistency 矛盾 finding
    cross = [f for f in findings if f["dimension"] == "crossConsistency"]
    assert cross, "应产出 crossConsistency 矛盾 finding"
    assert "不向境外提供" in cross[0]["description"]
    assert "d5" in dims  # 打回 d5 重审


def test_critic_no_outbound_no_conflict():
    """声明不出境 + 图谱无出境路径 → 无矛盾。"""
    critic = Critic(document_declares_no_outbound=True)
    findings, dims = critic.analyze(
        task_id="t",
        findings=[{"dimension": "d5CrossBorder", "verdict": "compliant", "level": "low"}],
        graph_summary="（无出境风险路径）",
    )
    cross = [f for f in findings if f["dimension"] == "crossConsistency"]
    assert cross == []
    assert "d5" not in dims


def test_critic_detects_behavior_declaration_conflict():
    """声明-行为矛盾：跨境不合规 + 图谱有出境 → 行为与义务不一致。"""
    critic = Critic(document_declares_no_outbound=False)
    findings, dims = critic.analyze(
        task_id="t",
        findings=[
            {
                "dimension": "d5CrossBorder",
                "verdict": "nonCompliant",
                "level": "high",
                "clauseRef": "第40条",
            }
        ],
        graph_summary="存在跨境出境路径",
    )
    cross = [f for f in findings if f["dimension"] == "crossConsistency"]
    assert cross, "应识别跨境行为与义务矛盾"
    assert "不一致" in cross[0]["description"]
    assert "d5" in dims


def test_critic_review_high_risk():
    """高风险结论复核：needsHumanReview=true 的高风险 finding → 联动标记。"""
    critic = Critic()
    findings, _ = critic.analyze(
        task_id="t",
        findings=[
            {
                "dimension": "d1Collection",
                "verdict": "unclear",
                "level": "high",
                "needsHumanReview": True,
                "clauseRef": "待补",
            }
        ],
        graph_summary="",
    )
    cross = [f for f in findings if f["dimension"] == "crossConsistency"]
    assert cross, "高风险待复核 finding 应联动产出 crossConsistency 标记"
    assert "待复核" in cross[0]["description"]
    assert cross[0]["needsHumanReview"] is True


# ── M5-3 反思循环：Critic 打回维度重跑 ≤2 轮 ──


def test_reflection_loop_forced_termination():
    """Critic 打回维度触发反思，但 ≤2 轮强制结束（防死循环）。"""
    import json

    from app.agents.workflow import MAX_REFLECTION_ROUNDS

    calls = {"d5": 0}

    async def noncompliant_d5(**kwargs):
        calls["d5"] += 1
        return json.dumps(
            {
                "dimension": "d5CrossBorder",
                "verdict": "nonCompliant",
                "level": "high",
                "clauseRef": "第40条",
                "description": "跨境未获单独同意",
                "remediation": "取得单独同意",
                "confidence": 0.8,
                "needsHumanReview": False,
            },
            ensure_ascii=False,
        )

    def make_clean(dim):
        async def agent(**kwargs):
            return json.dumps(
                {
                    "dimension": {
                        "d1": "d1Collection",
                        "d2": "d2Notice",
                        "d3": "d3Purpose",
                        "d4": "d4ThirdParty",
                        "d6": "d6DataRights",
                    }[dim],
                    "verdict": "compliant",
                    "level": "low",
                    "clauseRef": "第一条",
                    "description": "ok",
                    "remediation": "",
                    "confidence": 0.9,
                    "needsHumanReview": False,
                },
                ensure_ascii=False,
            )

        return agent

    agent_fns = {"d5": noncompliant_d5}
    for dim in ["d1", "d2", "d3", "d4", "d6"]:
        agent_fns[dim] = make_clean(dim)

    graph = build_workflow(agent_fns)
    result = asyncio.run(
        graph.ainvoke(
            {
                "task_id": "t",
                "document_id": "",
                "document_text": "文本",
                "retrieval": "（检索）",
                "graph_summary": "检测到跨境出境路径，风险高",
                "declares_no_outbound": True,
            }
        )
    )
    # d5 被打回重审，但调用次数 ≤ 初轮 + 反思轮（≤2 轮）
    assert calls["d5"] <= 1 + MAX_REFLECTION_ROUNDS
    # 产出 crossConsistency 矛盾 finding
    dims = {f["dimension"] for f in result["findings"]}
    assert "crossConsistency" in dims
