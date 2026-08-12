"""M3-3 验收测试：LLM 抽取通道（mock）+ 双通道合并（冲突保留 LLM + 低置信度）。

覆盖：
- mock LLM 调用路径（调用文本被记录）；
- LLM 输出 JSON 解析（合法项 + 非法枚举丢弃）；
- 有歧义案例：同实体规则判 controller、LLM 判 processor → 保留 LLM + 低置信度；
- 冲突边：属性冲突 → 保留 LLM + 低置信度；
- LLM 独有 / 规则独有均保留。
"""

from app.core.enums import EdgeType, EntityRole
from app.graph.builder import EdgeSpec, EntitySpec
from app.graph.llm_extractor import MockExtractionLLM, parse_llm_result
from app.graph.merger import merge_channels
from app.graph.rule_extractor import RuleExtraction

# ── LLM 通道调用路径 + 输出解析 ──


def test_mock_llm_call_path():
    """mock LLM 被调用且调用文本被记录（验证调用路径）。"""
    llm = MockExtractionLLM(canned={"entities": [], "edges": []})
    llm.extract("某隐私政策文本")
    assert len(llm.calls) == 1
    assert "隐私政策" in llm.calls[0]


def test_parse_llm_result_valid():
    """LLM 输出 JSON 解析为实体/边，枚举合法。"""
    raw = {
        "entities": [
            {"name": "云服务商", "role": "processor"},
            {"name": "手机号", "role": "dataCategory", "isSensitive": True},
        ],
        "edges": [
            {"source": "我们", "target": "手机号", "edgeType": "collect", "legalBasis": "合同"},
        ],
    }
    result = parse_llm_result(raw)
    assert len(result.entities) == 2
    assert any(e.name == "手机号" and e.is_sensitive for e in result.entities)
    assert len(result.edges) == 1
    assert result.edges[0].edge_type == EdgeType.COLLECT
    assert result.edges[0].legal_basis == "合同"


def test_parse_llm_result_discards_invalid():
    """非法角色/边类型被丢弃（不崩溃、不污染）。"""
    raw = {
        "entities": [
            {"name": "合法实体", "role": "controller"},
            {"name": "非法角色", "role": "unknownRole"},
        ],
        "edges": [
            {"source": "A", "target": "B", "edgeType": "badType"},
            {"source": "A", "target": "B", "edgeType": "share"},
        ],
    }
    result = parse_llm_result(raw)
    assert len(result.entities) == 1
    assert result.entities[0].name == "合法实体"
    assert len(result.edges) == 1
    assert result.edges[0].edge_type == EdgeType.SHARE


# ── 双通道合并：有歧义案例 ──


def test_merge_conflict_prefers_llm_and_low_confidence():
    """有歧义案例：同实体规则判 controller、LLM 判 processor → 保留 LLM + 低置信度。"""
    rule = RuleExtraction(
        entities=[EntitySpec(name="数据平台", role=EntityRole.CONTROLLER)],
        edges=[],
    )
    llm_raw = {
        "entities": [{"name": "数据平台", "role": "processor"}],
        "edges": [],
    }
    llm = parse_llm_result(llm_raw)

    merged = merge_channels(rule, llm)

    # 保留 LLM 角色（processor）
    assert len(merged.entities) == 1
    assert merged.entities[0].role == EntityRole.PROCESSOR
    # 标记低置信度
    assert ("entity", "数据平台") in merged.low_confidence


def test_merge_conflict_edge_prefers_llm():
    """冲突边：规则 legal_basis 与 LLM 不同 → 保留 LLM + 低置信度。"""
    rule = RuleExtraction(
        entities=[],
        edges=[
            EdgeSpec(
                "A",
                "B",
                EdgeType.SHARE,
                EntityRole.CONTROLLER,
                EntityRole.PROCESSOR,
                legal_basis="规则依据",
                is_risk=False,
            ),
        ],
    )
    llm = parse_llm_result(
        {
            "entities": [],
            "edges": [
                {
                    "source": "A",
                    "target": "B",
                    "edgeType": "share",
                    "legalBasis": "LLM依据",
                    "isRisk": True,
                },
            ],
        }
    )

    merged = merge_channels(rule, llm)

    assert len(merged.edges) == 1
    edge = merged.edges[0]
    assert edge.legal_basis == "LLM依据"
    assert edge.is_risk is True
    assert ("edge", "A::B::share") in merged.low_confidence


def test_merge_keeps_unique_from_both():
    """LLM 独有与规则独有均保留。"""
    rule = RuleExtraction(
        entities=[EntitySpec(name="规则独有实体", role=EntityRole.CONTROLLER)],
        edges=[
            EdgeSpec(
                "规则独有实体",
                "X",
                EdgeType.STORE,
                EntityRole.CONTROLLER,
                EntityRole.DATA_CATEGORY,
            )
        ],
    )
    llm = parse_llm_result(
        {
            "entities": [{"name": "LLM独有实体", "role": "processor"}],
            "edges": [{"source": "LLM独有实体", "target": "Y", "edgeType": "store"}],
        }
    )

    merged = merge_channels(rule, llm)

    names = {e.name for e in merged.entities}
    assert "规则独有实体" in names
    assert "LLM独有实体" in names
    assert len(merged.edges) == 2
    assert merged.low_confidence == []  # 无冲突不标记


def test_merge_same_entity_same_role_no_conflict():
    """同实体同角色：无冲突，不标低置信。"""
    rule = RuleExtraction(entities=[EntitySpec(name="平台", role=EntityRole.CONTROLLER)], edges=[])
    llm = parse_llm_result({"entities": [{"name": "平台", "role": "controller"}], "edges": []})

    merged = merge_channels(rule, llm)
    assert merged.entities[0].role == EntityRole.CONTROLLER
    assert merged.low_confidence == []
