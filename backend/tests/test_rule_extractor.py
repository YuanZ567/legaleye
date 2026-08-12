"""M3-2 验收测试：规则抽取通道（词典+正则）。

用真实 demo 隐私政策文本验证：
- 实体抽取（controller/processor/overseasReceiver/dataCategory + 敏感标记）；
- 关系抽取（collect/entrust/crossBorder → EdgeSpec）；
- 去重与确定性。
"""

from app.core.enums import EdgeType, EntityRole
from app.graph.rule_extractor import extract_by_rules

_DEMO = (
    "我们（个人信息处理者）为提供电商服务，收集您的手机号和账号信息。"
    "我们委托云服务商存储个人信息。"
    "我们向境外子公司跨境提供用户手机号，用于数据分析。"
)


def test_extract_entities():
    """实体抽取：controller/processor/overseasReceiver/dataCategory 与敏感标记。"""
    result = extract_by_rules(_DEMO)
    entities = {(e.name, e.role): e.is_sensitive for e in result.entities}

    # 处理者 -> controller
    assert any(r == EntityRole.CONTROLLER for (_, r) in entities)
    # 数据类别（手机号）敏感标记
    phone = next(
        (e for e in result.entities if e.role == EntityRole.DATA_CATEGORY and "手机号" in e.name),
        None,
    )
    assert phone is not None and phone.is_sensitive is True
    # 云服务商 -> processor
    assert any(r == EntityRole.PROCESSOR for (_, r) in entities)
    # 境外子公司 -> overseasReceiver
    assert any(r == EntityRole.OVERSEAS_RECEIVER for (_, r) in entities)


def test_extract_edges():
    """关系抽取：collect/entrust/crossBorder 边，跨境边 is_risk=True。"""
    result = extract_by_rules(_DEMO)
    edge_types = {(e.source, e.target, e.edge_type): e.is_risk for e in result.edges}

    # 收集手机号 -> collect 边
    assert any(t == EdgeType.COLLECT for (_, _, t) in edge_types)
    # 委托存储 -> entrust 边
    assert any(t == EdgeType.ENTRUST for (_, _, t) in edge_types)
    # 跨境提供 -> crossBorder 边 且 is_risk=True
    cross = [
        (s, tt, r)
        for (s, tt, r) in [(k[0], k[2], v) for k, v in edge_types.items()]
        if tt == EdgeType.CROSS_BORDER
    ]
    assert cross, "应存在跨境边"
    assert cross[0][2] is True


def test_extract_deterministic():
    """同一文本重复抽取结果一致（确定性）。"""
    r1 = extract_by_rules(_DEMO)
    r2 = extract_by_rules(_DEMO)
    assert len(r1.entities) == len(r2.entities)
    assert len(r1.edges) == len(r2.edges)
    assert [(e.name, e.role) for e in r1.entities] == [(e.name, e.role) for e in r2.entities]


def test_extract_empty_text():
    """空文本/无关系文本 → 无实体无边。"""
    assert extract_by_rules("").entities == []
    assert extract_by_rules("这是一段无关说明。").edges == []
