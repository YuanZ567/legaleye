"""M4-4 验收测试：六维审查节点（真实 LLM 经 factory + 强校验 + 降级）。

- LLM 返回合法 JSON → 过 validators → 返回合法 finding；
- LLM 返回非法枚举 → 校验丢弃 → 降级待补；
- LLM 抛异常 → 降级待补 + needsHumanReview=true（任务不中断）。
"""

import asyncio

from app.agents.dimension_agent import build_dimension_node


def _run(node, **state):
    base = {"task_id": "t", "document_text": "d", "retrieval": "", "graph_summary": ""}
    base.update(state)
    return asyncio.run(node(base))


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
    """LLM 返回合法 JSON 且 clauseRef 命中检索 → 过 validators 返回合法 finding。"""
    node = build_dimension_node("d1", _ok_llm)
    result = _run(node, retrieval="[第五条第1款 · 个人信息保护法] 收集应当最小必要")
    finding = result["findings"][0]
    assert finding["dimension"] == "d1Collection"
    assert finding["verdict"] == "nonCompliant"
    assert finding["confidence"] == 0.9
    assert finding["clauseRef"] == "第五条第1款"


def test_node_handles_invalid_enum_with_default():
    """LLM 返回非法 verdict → 默认 unclear 保留（不丢弃不降级）。"""
    node = build_dimension_node("d1", _invalid_llm)
    result = _run(node)
    finding = result["findings"][0]
    assert finding["dimension"] == "d1Collection"
    assert finding["verdict"] == "unclear"  # 非法 verdict 默认值
    assert finding["needsHumanReview"] is True  # verdict 非法标记人工复核


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


# ── D5 修复：clauseRef 检索命中校验（红线：禁无引用结论） ──


def test_clause_ref_must_hit_retrieval():
    """clauseRef 在检索结果中 → 保留（D5 修复核心）。"""
    from app.agents.dimension_agent import _normalize_llm_raw

    retrieval = "[第三十九条 · 个人信息保护法] 向境外提供个人信息应当取得单独同意"
    raw = _normalize_llm_raw(
        {"dimension": "d5CrossBorder", "clauseRef": "第三十九条", "conclusion": "不合规"},
        "d5",
        retrieval=retrieval,
    )
    assert raw["clauseRef"] == "第三十九条"  # 命中检索，保留
    assert raw["needsHumanReview"] is False


def test_clause_ref_fake_hit_cleared():
    """clauseRef 不在检索结果 → 清空 + needsHumanReview + verdict=unclear（禁假引用）。"""
    from app.agents.dimension_agent import _normalize_llm_raw

    retrieval = "[第三十九条 · 个人信息保护法] 向境外提供应当单独同意"
    # LLM 凭记忆写"第二条"，但检索结果里没有第二条
    raw = _normalize_llm_raw(
        {"dimension": "d5CrossBorder", "clauseRef": "第二条", "conclusion": "不合规"},
        "d5",
        retrieval=retrieval,
    )
    assert raw["clauseRef"] == ""  # 假引用清空
    assert raw["verdict"] == "unclear"
    assert raw["needsHumanReview"] is True


def test_clause_ref_no_retrieval_cleared():
    """无检索结果却写引用 → 清空 + 人工复核（红线兜底）。"""
    from app.agents.dimension_agent import _normalize_llm_raw

    raw = _normalize_llm_raw(
        {"dimension": "d5CrossBorder", "clauseRef": "第三十九条", "conclusion": "不合规"},
        "d5",
        retrieval="",
    )
    assert raw["clauseRef"] == ""
    assert raw["needsHumanReview"] is True
