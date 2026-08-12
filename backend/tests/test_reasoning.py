"""M3-4 验收测试：R1-R4 推理（在已建图谱上执行路径检测与建议）。

构造含敏感数据类别 → 跨境 → 境外接收方的 demo 图谱，验证：
- R1 出境可达路径（含 crossBorder 边）；
- R2 未获单独同意出境（crossBorder 边无同意依据 → 高风险）；
- R3 声明-图谱矛盾（声明不出境但有 crossBorder → 冲突）；
- R4 路径判定建议（敏感出境 → securityAssessment）。
"""

from app.core.enums import EdgeType, EntityRole, PathType, RiskLevel
from app.graph.builder import EdgeSpec, EntitySpec, GraphBuilder
from app.graph.reasoning import Reasoner


def _build_demo_graph(with_consent: bool = False) -> GraphBuilder:
    """构建 demo 图谱：电商平台收集手机号 → 委托云服务商 → 跨境给境外子公司。"""
    builder = GraphBuilder()
    builder.build(
        entities=[
            EntitySpec(name="电商平台", role=EntityRole.CONTROLLER),
            EntitySpec(name="云服务商", role=EntityRole.PROCESSOR),
            EntitySpec(name="境外子公司", role=EntityRole.OVERSEAS_RECEIVER),
            EntitySpec(name="用户手机号", role=EntityRole.DATA_CATEGORY, is_sensitive=True),
        ],
        edges=[
            EdgeSpec(
                "电商平台",
                "用户手机号",
                EdgeType.COLLECT,
                EntityRole.CONTROLLER,
                EntityRole.DATA_CATEGORY,
            ),
            EdgeSpec(
                "电商平台",
                "云服务商",
                EdgeType.ENTRUST,
                EntityRole.CONTROLLER,
                EntityRole.PROCESSOR,
            ),
            EdgeSpec(
                "云服务商",
                "境外子公司",
                EdgeType.CROSS_BORDER,
                EntityRole.PROCESSOR,
                EntityRole.OVERSEAS_RECEIVER,
                legal_basis="经用户单独同意" if with_consent else None,
                is_risk=True,
            ),
        ],
    )
    return builder


def test_r1_reachable_outbound_path():
    """R1：敏感数据存在出境可达路径（含 crossBorder 边）。"""
    reasoner = Reasoner(_build_demo_graph().graph)
    paths = reasoner.reachable_outbound_paths()
    assert paths, "应检测到出境可达路径"
    # 敏感出境路径：contains_sensitive=True 且 level=HIGH
    sensitive_paths = [p for p in paths if p.contains_sensitive]
    assert sensitive_paths, "应检测到含敏感数据的出境路径"
    assert sensitive_paths[0].level == RiskLevel.HIGH
    # 路径终点为境外子公司，且经过手机号敏感源
    assert sensitive_paths[0].path[-1] == "境外子公司"
    assert "用户手机号" in sensitive_paths[0].path


def test_r2_unauthorized_cross_border():
    """R2：crossBorder 边无单独同意 → 高风险未授权出境。"""
    reasoner = Reasoner(_build_demo_graph().graph)  # 无 legal_basis
    risks = reasoner.unauthorized_cross_border_edges()
    assert risks, "应识别未获同意的出境"
    assert risks[0].reason == "出境未经单独同意"
    assert risks[0].level == RiskLevel.HIGH


def test_r2_consented_cross_border_not_flagged():
    """R2：crossBorder 边含单独同意依据 → 不标记。"""
    reasoner = Reasoner(_build_demo_graph(with_consent=True).graph)
    risks = reasoner.unauthorized_cross_border_edges()
    assert risks == []


def test_r3_declaration_conflict():
    """R3：声明不出境但有 crossBorder 边 → 矛盾冲突。"""
    reasoner = Reasoner(_build_demo_graph().graph, declares_no_outbound=True)
    conflicts = reasoner.declaration_conflict()
    assert conflicts, "应识别声明-图谱矛盾"
    assert "不向境外提供" in conflicts[0].reason

    # 无 crossBorder 时不冲突
    reasoner2 = Reasoner(GraphBuilder().graph, declares_no_outbound=True)
    assert reasoner2.declaration_conflict() == []


def test_r4_sensitive_outbound_suggests_assessment():
    """R4：敏感出境路径 → 建议安全评估。"""
    reasoner = Reasoner(_build_demo_graph().graph)
    risk_records = reasoner.unauthorized_cross_border_edges() + reasoner.reachable_outbound_paths()
    suggestions = reasoner.suggestions(risk_records)
    assert suggestions, "应有整改建议"
    assert any(s["pathType"] == PathType.SECURITY_ASSESSMENT for s in suggestions)
    assert any(s["level"] == RiskLevel.HIGH for s in suggestions)


def test_r4_no_risk_no_suggestion():
    """R4：无风险记录 → 无建议。"""
    reasoner = Reasoner(_build_demo_graph(with_consent=True).graph)
    assert reasoner.suggestions([]) == []
