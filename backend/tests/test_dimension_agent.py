"""M4-4 验收测试：六维审查节点（真实 LLM 经 factory + 强校验 + 降级）。

- LLM 返回合法 JSON → 过 validators → 返回合法 finding；
- LLM 返回非法枚举 → 校验丢弃 → 降级待补；
- LLM 抛异常 → 降级待补 + needsHumanReview=true（任务不中断）。
"""

import asyncio

from app.agents.dimension_agent import build_dimension_node


def _run(node, **state):
    return asyncio.run(
        node(state or {"task_id": "t", "document_text": "d", "retrieval": "", "graph_summary": ""})
    )


async def _ok_llm(**kwargs):
    return (
        '{"dimension":"d1Collection","verdict":"nonCompliant","level":"high",'
        '"clauseRef":"第五条第1款","description":"超出最小必要","remediation":"缩减",'
        '"confidence":0.9,"needsHumanReview":false}'
    )


async def _invalid_llm(**kwargs):
    # 非法 verdict 枚举
    return '{"dimension":"d1Collection","verdict":"nope","level":"high","clauseRef":"第一条"}'


async def _raise_llm(**kwargs):
    raise RuntimeError("LLM 网络超时")


def test_node_returns_valid_finding():
    """LLM 返回合法 JSON → 过 validators 返回合法 finding。"""
    node = build_dimension_node("d1", _ok_llm)
    result = _run(node)
    finding = result["findings"][0]
    assert finding["dimension"] == "d1Collection"
    assert finding["verdict"] == "nonCompliant"
    assert finding["confidence"] == 0.9
    assert finding["clauseRef"] == "第五条第1款"


def test_node_degrades_on_invalid_enum():
    """LLM 返回非法枚举 → 校验丢弃 → 降级待补。"""
    node = build_dimension_node("d1", _invalid_llm)
    result = _run(node)
    finding = result["findings"][0]
    assert finding["clauseRef"] == "待补"
    assert finding["needsHumanReview"] is True


def test_node_degrades_on_llm_exception():
    """LLM 抛异常 → 降级待补 + needsHumanReview（任务不中断）。"""
    node = build_dimension_node("d1", _raise_llm)
    result = _run(node)
    finding = result["findings"][0]
    assert finding["clauseRef"] == "待补"
    assert finding["needsHumanReview"] is True
    assert "降级" in finding["description"]


def test_node_passes_retrieval_to_llm():
    """节点把检索结果/文档文本传给 LLM（依据检索而非记忆）。"""
    captured = {}

    async def capture_llm(**kwargs):
        captured["messages"] = kwargs["messages"]
        return (
            '{"dimension":"d1Collection","verdict":"compliant","level":"low","clauseRef":"第一条"}'
        )

    node = build_dimension_node("d1", capture_llm)
    _run(node, task_id="t1", document_text="隐私政策原文", retrieval="检索结果A")
    msgs = captured["messages"]
    assert msgs[0]["role"] == "system"  # 提示词 system
    assert "检索结果A" in msgs[1]["content"]  # 检索结果传入
    assert "隐私政策原文" in msgs[1]["content"]  # 文档原文传入
