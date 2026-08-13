"""M4-2 验收测试：prompts 集中管理 + LLM finding 强校验。

- D1-D6 提示词集中在 prompts/ 注册表，system 含"依据检索结果而非记忆"纪律；
- validators：clauseRef 正则失败→pending+needsHumanReview、confidence 钳制 [0,1]、
  枚举未知丢弃、缺失字段默认、无命中输出"待补"。
"""

import pytest
from app.prompts import get_prompt
from app.schemas.validators import validate_finding

# ── prompts 集中管理 ──


def test_all_six_dimensions_registered():
    """D1-D6 六维度提示词均可获取且字段齐全。"""
    for dim in ["d1", "d2", "d3", "d4", "d5", "d6"]:
        spec = get_prompt(dim)
        assert spec.dimension == dim
        assert spec.system and spec.user_template and spec.output_schema
        assert "{document}" in spec.user_template or "{context}" in spec.user_template


def test_prompt_contains_retrieval_discipline():
    """提示词 system 含"依据检索结果而非记忆"纪律（无命中输出待补）。"""
    for dim in ["d1", "d2", "d3", "d4", "d5", "d6"]:
        spec = get_prompt(dim)
        assert "依据" in spec.system
        assert "待补" in spec.system or "needsHumanReview" in spec.system


def test_get_prompt_unknown_dimension_raises():
    """未知维度 → KeyError。"""
    with pytest.raises(KeyError):
        get_prompt("d9")


# ── validators：强校验 ──


def _valid_raw(**overrides):
    base = {
        "dimension": "d1Collection",
        "verdict": "nonCompliant",
        "level": "high",
        "clauseRef": "第五条第1款",
        "statuteVersion": "个人信息保护法(2021)",
        "description": "收集范围超出最小必要",
        "remediation": "缩减收集范围",
        "confidence": 0.8,
        "needsHumanReview": False,
        "evidence": {"text": "原文", "charRange": [0, 5]},
    }
    base.update(overrides)
    return base


def test_valid_finding_passes():
    """合法 finding 原样通过（clauseRef 匹配正则）。"""
    result, warnings = validate_finding(_valid_raw())
    assert result is not None
    assert warnings == []
    assert result["dimension"] == "d1Collection"
    assert result["confidence"] == 0.8


def test_clause_ref_invalid_degrades_to_pending():
    """clauseRef 非法 → 降级待补 + needsHumanReview=true（verdict 保持原值，不丢弃）。"""
    result, warnings = validate_finding(_valid_raw(clauseRef="第十二章"))
    assert result is not None
    assert result["clauseRef"] == "待补"
    assert result["verdict"] == "nonCompliant"  # verdict 保持原值
    assert result["needsHumanReview"] is True
    assert any("clauseRef" in w for w in warnings)


def test_confidence_clamped():
    """confidence 钳制到 [0,1]；越界/NaN 处理。"""
    assert validate_finding(_valid_raw(confidence=1.5))[0]["confidence"] == 1.0
    assert validate_finding(_valid_raw(confidence=-0.3))[0]["confidence"] == 0.0
    assert validate_finding(_valid_raw(confidence="abc"))[0]["confidence"] == 0.0
    import math

    assert validate_finding(_valid_raw(confidence=math.nan))[0]["confidence"] == 0.0


def test_unknown_enum_discarded():
    """枚举：dimension 未知丢弃；verdict/level 非法默认值保留（不丢弃）+ 告警。"""
    # 非法 dimension → 丢弃
    result, warnings = validate_finding(_valid_raw(dimension="d99"))
    assert result is None
    assert any("dimension" in w for w in warnings)
    # 非法 verdict → 默认 unclear（不丢弃）+ 告警
    result, warnings = validate_finding(_valid_raw(verdict="notAThing"))
    assert result is not None
    assert result["verdict"] == "unclear"
    assert any("verdict" in w for w in warnings)
    # 非法 level → 默认 medium（不丢弃）+ 告警
    result, warnings = validate_finding(_valid_raw(level="critical"))
    assert result is not None
    assert result["level"] == "medium"
    assert any("level" in w for w in warnings)


def test_no_hit_pending():
    """无命中（clauseRef='待补'）→ 保持 unclear + needsHumanReview（不降级）。"""
    result, warnings = validate_finding(
        _valid_raw(clauseRef="待补", verdict="unclear", needsHumanReview=True)
    )
    assert result is not None
    assert result["clauseRef"] == "待补"
    assert result["verdict"] == "unclear"
    assert result["needsHumanReview"] is True


def test_missing_fields_defaulted():
    """缺失可选字段 → 安全默认（statuteVersion=None、evidence=None）。"""
    raw = _valid_raw()
    raw.pop("statuteVersion")
    raw.pop("evidence")
    result, _ = validate_finding(raw)
    assert result is not None
    assert result["statuteVersion"] is None
    assert result["evidence"] is None
