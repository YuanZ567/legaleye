"""M6-1/2/3 验收测试：声明键抽取 + 名称归一化 + 矛盾级别判定。

- 6 声明键抽取（值 + 原文证据）；
- 名称归一化（境外/海外/overseas → 同一概念）；
- 矛盾判定（政策不出境 vs DPA 有境外接收方 → 高矛盾）；
- M6-4 样本：注入样本检出 ≥1 条高级矛盾。
"""

from app.core.enums import DeclarationKey, RiskLevel
from app.services.crossdoc import (
    compare_declarations,
    extract_declarations,
    judge_conflict_level,
    normalize_name,
)

_POLICY = (
    "我们收集您的手机号和账号信息，用于提供电商服务。"
    "我们不出境，所有个人信息均存储于境内服务器，保存期限为3年。"
    "您有权查询、更正、删除您的个人信息。"
)

_DPA = (
    "受托方处理的数据类别包括手机号、账号。处理目的为合同履行。"
    "处理者向境外子公司提供数据，跨境传输至海外服务器。保存期限为10年。"
)


# ── M6-1 声明键抽取 ──


def test_extract_all_six_declaration_keys():
    """从含全部声明的文本抽取出 6 类声明键（含证据）。"""
    full = (
        "我们收集您的手机号和账号信息，用于提供电商服务。"
        "我们向境外子公司提供数据，跨境传输。保存期限为3年。"
        "您有权查询、更正、删除您的个人信息。"
    )
    decls = extract_declarations(full)
    assert set(decls.keys()) == {
        DeclarationKey.DATA_CATEGORY,
        DeclarationKey.PURPOSE,
        DeclarationKey.RECEIVERS,
        DeclarationKey.CROSS_BORDER,
        DeclarationKey.RETENTION,
        DeclarationKey.RIGHTS,
    }
    # 每个声明带原文证据
    for decl in decls.values():
        assert decl.text


def test_extract_cross_border_negative():
    """政策声明"不出境"被正确识别为否定语义。"""
    decls = extract_declarations(_POLICY)
    cross = decls[DeclarationKey.CROSS_BORDER]
    assert "不出境" in cross.value


# ── M6-2 名称归一化 ──


def test_normalize_name_synonyms():
    """境外/海外/overseas 归一化为同一概念。"""
    assert normalize_name("向境外提供") == "境外"
    assert normalize_name("传输至海外服务器") == "境外"
    assert normalize_name("overseas") == "境外"


# ── M6-3 矛盾级别判定 ──


def test_cross_border_conflict_high():
    """政策不出境 vs DPA 有境外接收方 → crossBorder 高矛盾。"""
    policy_decls = extract_declarations(_POLICY)
    dpa_decls = extract_declarations(_DPA)
    a = policy_decls[DeclarationKey.CROSS_BORDER]
    b = dpa_decls[DeclarationKey.CROSS_BORDER]
    assert compare_declarations(a, b, doc_a=None, doc_b=None) is True
    assert judge_conflict_level(a, b) == RiskLevel.HIGH


def test_retention_conflict_medium():
    """保留期限不一致（3年 vs 10年）→ 中矛盾。"""
    policy_decls = extract_declarations(_POLICY)
    dpa_decls = extract_declarations(_DPA)
    a = policy_decls[DeclarationKey.RETENTION]
    b = dpa_decls[DeclarationKey.RETENTION]
    assert compare_declarations(a, b, doc_a=None, doc_b=None) is True
    assert judge_conflict_level(a, b) == RiskLevel.MEDIUM


# ── M6-4 样本：检出 ≥1 条高级矛盾 ──


def test_sample_detects_high_conflict():
    """注入样本（政策不出境 vs DPA 有境外接收方）检出 ≥1 条高级矛盾。"""
    policy = extract_declarations(_POLICY)
    dpa = extract_declarations(_DPA)

    high_conflicts = []
    for key in policy:
        if key in dpa:
            a, b = policy[key], dpa[key]
            if compare_declarations(a, b, doc_a=None, doc_b=None):
                high_conflicts.append((key, judge_conflict_level(a, b)))

    assert high_conflicts, "应检出至少一条矛盾"
    assert any(level == RiskLevel.HIGH for _, level in high_conflicts), "应含高级矛盾"
