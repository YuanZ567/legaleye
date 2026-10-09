"""M10.2 三层防误报防线测试（2026-09-15）：

第 1 层 `_apply_requirement_check`：要件核查纠偏（治误报，不造漏报）；
第 2 层 `_apply_compliance_exception`：合规信号豁免门（代码层第二道保险）；
第 3 层 `_apply_high_risk_rule`：规则触发前查合规信号（模板句规则不误伤真实文本）。

背景：真实政策盲测 7/7 全误报——模型只匹配"跨境/共享/广告推送"等触发词，
不核查"是否单独同意/是否给退订/是否告知权利"等合规要件。
"""

import asyncio

from app.agents.dimension_agent import (
    _apply_applicability_gate,
    _apply_compliance_exception,
    _apply_high_risk_rule,
    _apply_requirement_check,
    _extract_requirement_check,
    build_dimension_node,
)


def _finding(verdict="nonCompliant", **overrides):
    base = {
        "dimension": "d5CrossBorder",
        "verdict": verdict,
        "level": "high",
        "clauseRef": "第三十九条",
        "description": "文档向境外提供个人信息未取得单独同意",
        "remediation": "取得单独同意",
        "confidence": 0.9,
        "needsHumanReview": False,
        "evidence": {"text": "您的信息将存储在境外的服务器", "charRange": [0, 0]},
    }
    base.update(overrides)
    return base


# ── 第 1 层：要件核查纠偏 ──


def test_all_requirements_satisfied_downgrades_to_compliant():
    """模型报 nonCompliant 但要件全部 satisfied → 纠为 compliant（触发词误报）。"""
    f = _finding(requirement_check=[
        {"name": "单独同意", "status": "satisfied", "evidence": "单独获取您的授权同意"},
        {"name": "告知接收方", "status": "satisfied", "evidence": ""},
        {"name": "合法路径", "status": "satisfied", "evidence": "签署数据保护协议"},
    ])
    out = _apply_requirement_check(f)
    assert out["verdict"] == "compliant"
    assert out["needsHumanReview"] is False
    assert "要件核查" in out["description"]


def test_missing_requirement_keeps_noncompliant():
    """模型报 nonCompliant 且存在 missing 要件 → 维持，description 注明缺失项。"""
    f = _finding(requirement_check=[
        {"name": "单独同意", "status": "missing", "evidence": "未提及"},
        {"name": "合法路径", "status": "satisfied", "evidence": "标准合同"},
    ])
    out = _apply_requirement_check(f)
    assert out["verdict"] == "nonCompliant"
    assert "缺失要件：单独同意" in out["description"]


def test_unknown_requirement_goes_to_review():
    """模型报 nonCompliant 且要件状态含 unknown → 转 unclear + 人工复核。"""
    f = _finding(requirement_check=[
        {"name": "单独同意", "status": "unknown", "evidence": ""},
    ])
    out = _apply_requirement_check(f)
    assert out["verdict"] == "unclear"
    assert out["needsHumanReview"] is True


def test_no_requirement_check_untouched():
    """模型未输出 requirementCheck（兼容旧模型）→ 原样返回。"""
    f = _finding(requirement_check=None)
    out = _apply_requirement_check(f)
    assert out["verdict"] == "nonCompliant"


def test_compliant_verdict_not_escalated():
    """模型报 compliant + 要件 missing → 不升级（只降级纠偏，不造漏报）。"""
    f = _finding(verdict="compliant", requirement_check=[
        {"name": "单独同意", "status": "missing", "evidence": ""},
    ])
    out = _apply_requirement_check(f)
    assert out["verdict"] == "compliant"


# ── 第 2 层：合规信号豁免门 ──


def test_compliance_exception_on_signal():
    """nonCompliant + 文档含"单独同意" → 降级 unclear + 人工复核。"""
    f = _finding()
    out = _apply_compliance_exception(f, "向境外提供前将取得您的单独同意，并签订数据保护协议。")
    assert out["verdict"] == "unclear"
    assert out["needsHumanReview"] is True
    assert "合规信号豁免" in out["description"]


def test_compliance_exception_not_triggered_without_signal():
    """nonCompliant + 文档无合规信号 → 保持。"""
    f = _finding()
    out = _apply_compliance_exception(f, "您的信息将存储在境外的服务器，注册即视为同意。")
    assert out["verdict"] == "nonCompliant"


def test_compliance_exception_dimension_specific():
    """维度差异化信号：d5 命中"安全评估"，d3 命中共用"退订"。"""
    f5 = _finding()
    assert _apply_compliance_exception(f5, "我们完成了数据出境安全评估。")["verdict"] == "unclear"
    f3 = _finding(dimension="d3Purpose")
    assert _apply_compliance_exception(f3, "您可在设置中退订营销推送。")["verdict"] == "unclear"


# ── 第 3 层：规则触发前查合规信号 ──


def test_high_risk_rule_suppressed_by_compliance_signal():
    """文档含合规信号 + 命中"注册即视为同意" → 规则不强制报违规。"""
    f = _finding(verdict="compliant")
    doc = "您注册即视为同意该传输。同时我们提供单独同意机制供您选择。"
    out = _apply_high_risk_rule(f, doc, "d5")
    assert out["verdict"] == "compliant"  # 未触发规则


def test_high_risk_rule_fires_without_signal():
    """文档无合规信号 + 命中"注册即视为同意" → 强制 nonCompliant。"""
    f = _finding(verdict="compliant")
    doc = "您注册即视为同意该传输。"
    out = _apply_high_risk_rule(f, doc, "d5")
    assert out["verdict"] == "nonCompliant"
    assert "确定性规则兜底" in out["description"]


# ── 提取器边界 ──


def test_extract_requirement_check_boundaries():
    """非法 status / 非列表 / 空 → 规范化或 None。"""
    assert _extract_requirement_check({}) is None
    assert _extract_requirement_check({"requirementCheck": "nope"}) is None
    assert _extract_requirement_check({"requirementCheck": []}) is None
    assert _extract_requirement_check({"requirementCheck": [{"name": "", "status": "satisfied"}]}) is None
    rc = _extract_requirement_check({"requirementCheck": [
        {"name": "单独同意", "status": "SATISFIED", "evidence": "x"},
        {"name": "坏项", "status": "bad"},
    ]})
    assert rc == [{"name": "单独同意", "status": "satisfied", "evidence": "x"}]


# ── 节点集成：mock LLM 带 requirementCheck ──


def test_node_corrects_false_positive_end_to_end():
    """端到端：模型对真实合规文档报 nonCompliant + 要件全 satisfied → 节点输出 compliant。"""

    async def llm(**kwargs):
        return (
            '{"dimension":"d5CrossBorder","verdict":"nonCompliant","level":"high",'
            '"clauseRef":"第三十九条","description":"文档向境外提供个人信息",'
            '"remediation":"取得单独同意","confidence":0.9,"needsHumanReview":false,'
            '"evidence":{"text":"如您使用跨境交易服务，我们会单独获取您的授权同意","charRange":[0,0]},'
            '"requirementCheck":['
            '{"name":"单独同意","status":"satisfied","evidence":"单独获取您的授权同意"},'
            '{"name":"告知接收方","status":"satisfied","evidence":""},'
            '{"name":"合法路径","status":"satisfied","evidence":"数据保护协议"}]}'
        )

    node = build_dimension_node("d5", llm)

    async def run():
        return await node({
            "task_id": "t",
            "document_text": "如您使用跨境交易服务，我们会单独获取您的授权同意，并要求接收方按照双方签署的数据保护协议处理您的个人信息。",
            "retrieval": "[第三十九条] 向境外提供个人信息应当取得单独同意",
            "graph_summary": "",
        })

    finding = asyncio.run(run())["findings"][0]
    assert finding["verdict"] == "compliant"
    assert finding["dimension"] == "d5CrossBorder"


# ── M11（2026-09-19）：软性合规表述豁免（支付宝 r07 误报修复）──


def test_compliance_exception_soft_signal_d1():
    """d1 误报场景：支付宝『为提升服务体验…收集操作记录，如您不提供不影响使用』→ 豁免。"""
    f = _finding(dimension="d1Collection", clauseRef="第五条")
    doc = (
        "为了提升您的服务体验及改进服务质量，或者为您推荐更优质或适合的服务，"
        "我们会收集您使用我们服务的操作记录。如您不提供前述信息，不影响您使用我们提供的其他服务。"
    )
    out = _apply_compliance_exception(f, doc)
    assert out["verdict"] == "unclear"
    assert out["needsHumanReview"] is True


def test_compliance_exception_soft_signal_d4():
    """d4 误报场景：支付宝『基于法定义务以及为向您提供服务所必需的要求…必要信息』→ 豁免。"""
    f = _finding(dimension="d4ThirdParty", clauseRef="第二十二条")
    doc = (
        "您可通过客户端使用我们、我们的关联方、我们合作的第三方服务方提供的各类服务，"
        "根据各服务实际提供方基于法定义务以及为向您提供服务所必需的要求，"
        "我们会向其提供或通过其获取您所使用服务的账号标识、订单、相关服务日志信息等必要信息。"
        "对于其他信息，您可以通过我们提供的信息授权服务进行信息共享。"
    )
    out = _apply_compliance_exception(f, doc)
    assert out["verdict"] == "unclear"
    assert out["needsHumanReview"] is True


def test_compliance_exception_soft_signal_not_overbroad():
    """软性信号不放宽到病句：无合规信号的违规文本不被豁免（防止过度豁免导致漏检）。"""
    f = _finding(dimension="d1Collection", clauseRef="第五条")
    doc = "我们会收集您的全部个人信息并永久保存，用于向第三方出售。"  # 无任何软性合规信号
    out = _apply_compliance_exception(f, doc)
    assert out["verdict"] == "nonCompliant"


# ── M12（2026-09-20）：适用性预筛门（跨境合同漏检修复）──


def test_applicability_gate_crossborder_signal_downgrades_not_applicable():
    """c08 漏检场景：Stripe DPA 含 Cross-border Data Transfers，d5 判 notApplicable → 转人工复核。"""
    f = _finding(verdict="notApplicable", dimension="d5CrossBorder", clauseRef="")
    doc = (
        "6. Data transfers. 6.1 Cross-border Data Transfers by User. "
        "User transfers Personal Data to Stripe, LLC in the United States."
    )
    out = _apply_applicability_gate(f, doc, "d5")
    assert out["verdict"] == "unclear"
    assert out["needsHumanReview"] is True
    assert "适用性预筛" in out["description"]


def test_applicability_gate_no_signal_keeps_not_applicable():
    """无适用信号的 notApplicable 保持原判（不误伤真正不适用场景）。"""
    f = _finding(verdict="notApplicable", dimension="d5CrossBorder", clauseRef="")
    doc = "本文件仅为软件使用许可协议，不涉及任何个人数据传输。"
    out = _apply_applicability_gate(f, doc, "d5")
    assert out["verdict"] == "notApplicable"


def test_applicability_gate_ignores_non_not_applicable():
    """预筛门只动 notApplicable；nonCompliant / compliant / unclear 不受影响。"""
    for v in ("nonCompliant", "compliant", "unclear"):
        f = _finding(verdict=v, dimension="d5CrossBorder")
        doc = "cross-border data transfer of personal data to the United States."
        out = _apply_applicability_gate(f, doc, "d5")
        assert out["verdict"] == v


# ── M13（2026-09-21）：DPA 合同语境豁免（微软 c06 d1 误报修复）──


def test_dpa_documented_instructions_d1_exception():
    """c06 误报场景：微软 DPA『仅按客户 documented instructions 处理，数据类别见附录』→ 豁免。"""
    f = _finding(dimension="d1Collection", clauseRef="第五条")
    doc = (
        "Microsoft will use and otherwise process Customer Data only as described "
        "and subject to the limitations provided below to provide Customer the "
        "Products and Services in accordance with Customer's documented instructions. "
        "Appendix B - Data Subjects and Categories of Personal Data."
    )
    out = _apply_compliance_exception(f, doc)
    assert out["verdict"] == "unclear"
    assert out["needsHumanReview"] is True


def test_dpa_signal_not_overbroad_for_real_privacy_policy():
    """信号不放宽到隐私政策：真实隐私政策报 d1 违规不被豁免（DPA 短语不出现）。"""
    f = _finding(dimension="d1Collection", clauseRef="第五条")
    doc = (
        "我们会收集您的全部个人信息并永久保存，用于向第三方出售，"
        "且不提供任何拒绝方式。"
    )
    out = _apply_compliance_exception(f, doc)
    assert out["verdict"] == "nonCompliant"


def test_dpa_signal_no_false_trigger_on_bad_contract():
    """恶意合同即使含 'data exporter' 字样但确有违规表述，其他豁免信号缺失时仍报违规。"""
    f = _finding(dimension="d1Collection", clauseRef="第五条")
    doc = (
        "The data exporter shall collect all personal data of every user without "
        "any consent and sell them to third parties."
    )
    out = _apply_compliance_exception(f, doc)
    assert out["verdict"] == "nonCompliant"
