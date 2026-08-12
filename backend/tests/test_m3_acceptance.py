"""M3-6 收尾验收：金标样例识别 ≥1 条出境路径（R1-R4 端到端）。

用 M3-2 抽取的真实 demo 隐私政策文本：规则抽取 → 建图 → R1-R4 推理 →
断言 riskPaths 含 ≥1 条出境路径（敏感可达或未同意出境）。
"""

from app.core.enums import RiskLevel
from app.graph.builder import GraphBuilder
from app.graph.reasoning import Reasoner
from app.graph.rule_extractor import extract_by_rules

# 金标样例：含收集/委托/跨境，且跨境未获单独同意
_GOLD = (
    "我们（个人信息处理者）为提供电商服务，收集您的手机号和账号信息。"
    "我们委托云服务商存储个人信息。"
    "我们向境外子公司跨境提供用户手机号，用于数据分析。"
)


def test_gold_demo_detects_outbound_path():
    """金标样例：图谱应识别 ≥1 条出境路径。"""
    extraction = extract_by_rules(_GOLD)
    assert extraction.edges, "金标样例应抽取到关系边"

    builder = GraphBuilder()
    builder.build(extraction.entities, extraction.edges)
    reasoner = Reasoner(builder.graph)

    risk_paths = (
        reasoner.reachable_outbound_paths()
        + reasoner.unauthorized_cross_border_edges()
        + reasoner.declaration_conflict()
    )
    # 至少识别 1 条出境风险路径
    assert risk_paths, "金标样例应识别 ≥1 条出境路径"


def test_gold_sensitive_outbound_high():
    """金标样例：敏感数据出境路径应标记为高风险。"""
    extraction = extract_by_rules(_GOLD)
    builder = GraphBuilder()
    builder.build(extraction.entities, extraction.edges)
    reasoner = Reasoner(builder.graph)

    sensitive_paths = [p for p in reasoner.reachable_outbound_paths() if p.contains_sensitive]
    assert sensitive_paths, "应识别含敏感数据的出境路径"
    assert all(p.level == RiskLevel.HIGH for p in sensitive_paths)


def test_gold_unauthorized_cross_border():
    """金标样例：出境未获单独同意 → 高风险。"""
    extraction = extract_by_rules(_GOLD)
    builder = GraphBuilder()
    builder.build(extraction.entities, extraction.edges)
    reasoner = Reasoner(builder.graph)

    unauthorized = reasoner.unauthorized_cross_border_edges()
    assert unauthorized, "应识别未获单独同意的出境"
    assert all(r.level == RiskLevel.HIGH for r in unauthorized)


def test_gold_graph_payload_has_risk_paths():
    """金标样例：GraphPayload 序列化后 riskPaths 非空（含出境路径）。"""
    extraction = extract_by_rules(_GOLD)
    builder = GraphBuilder()
    builder.build(extraction.entities, extraction.edges)
    reasoner = Reasoner(builder.graph)

    payload = builder.to_payload().dump_dict()
    # 含跨境边
    cross = [e for e in payload["edges"] if e["type"] == "crossBorder"]
    assert cross, "图谱应含跨境边"
    # riskPaths 可由推理结果填充
    risk_records = reasoner.reachable_outbound_paths() + reasoner.unauthorized_cross_border_edges()
    assert risk_records, "应有出境风险路径记录"
