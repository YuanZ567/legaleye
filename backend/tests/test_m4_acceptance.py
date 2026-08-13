"""M4-7 收尾验收：finding 字段齐全 + 六维工作流 mock 端到端。

- ComplianceFinding 强字段齐全（dimension/verdict/level/clauseRef/statuteVersion/
  description/remediation/confidence/needsHumanReview）；
- finding 契约 camelCase 序列化；
- 六维工作流（mock LLM）产出 6 条字段齐全 finding。
"""

import asyncio
import json

from app.agents.workflow import DIMENSIONS, build_workflow
from app.schemas.validators import validate_finding

# 契约要求强字段（DATA_CONTRACT 4.8）
REQUIRED_FIELDS = {
    "dimension",
    "verdict",
    "level",
    "clauseRef",
    "statuteVersion",
    "description",
    "remediation",
    "confidence",
    "needsHumanReview",
}


def _finding_json(dimension: str) -> str:
    return json.dumps(
        {
            "dimension": _dim_contract(dimension),
            "verdict": "nonCompliant",
            "level": "high",
            "clauseRef": "第五条第1款",
            "statuteVersion": "个人信息保护法(2021)",
            "description": "收集范围超出最小必要",
            "remediation": "缩减收集范围",
            "confidence": 0.85,
            "needsHumanReview": False,
        },
        ensure_ascii=False,
    )


def _dim_contract(dim: str) -> str:
    return {
        "d1": "d1Collection",
        "d2": "d2Notice",
        "d3": "d3Purpose",
        "d4": "d4ThirdParty",
        "d5": "d5CrossBorder",
        "d6": "d6DataRights",
    }[dim]


def _make_llm(dimension: str):
    async def llm(**kwargs):
        return _finding_json(dimension)

    return llm


def test_finding_fields_complete():
    """单条 finding 强字段齐全（validators 规范化后）。"""
    raw = json.loads(_finding_json("d1"))
    finding, warnings = validate_finding(raw)
    assert finding is not None
    assert warnings == []
    assert REQUIRED_FIELDS <= set(finding.keys())


def test_workflow_produces_complete_findings():
    """六维工作流（mock LLM）产出 6 条字段齐全的 finding。"""
    agent_fns = {dim: _make_llm(dim) for dim in DIMENSIONS}
    graph = build_workflow(agent_fns)
    result = asyncio.run(
        graph.ainvoke(
            {
                "task_id": "t",
                "document_id": "",
                "document_text": "隐私政策文本",
                "retrieval": "（检索）",
                "graph_summary": "",
            }
        )
    )
    findings = result["findings"]
    assert len(findings) == 6
    for f in findings:
        assert REQUIRED_FIELDS <= set(f.keys())
        assert 0.0 <= f["confidence"] <= 1.0  # confidence 钳制在 [0,1]
        assert isinstance(f["needsHumanReview"], bool)


def test_finding_contract_camelcase():
    """finding 契约字段 camelCase（clauseRef/statuteVersion/needsHumanReview）。"""
    raw = json.loads(_finding_json("d1"))
    finding, _ = validate_finding(raw)
    assert finding["clauseRef"] == "第五条第1款"
    assert finding["statuteVersion"] == "个人信息保护法(2021)"
    assert finding["needsHumanReview"] is False
