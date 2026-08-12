"""M3-1 验收测试：图谱构建器（networkx 骨架 + GraphPayload 契约）。

覆盖：
- 实体/边去重（DATA_CONTRACT 4.10 validators：同 name+role / 同 from+to+type 合并）；
- networkx 有向图构建正确；
- GraphPayload 序列化对齐 4.7（camelCase + 枚举值）。
"""

import networkx as nx
from app.core.enums import EdgeType, EntityRole
from app.graph.builder import EdgeSpec, EntitySpec, GraphBuilder


def _build_example() -> GraphBuilder:
    builder = GraphBuilder()
    builder.build(
        entities=[
            EntitySpec(name="电商平台", role=EntityRole.CONTROLLER, is_sensitive=False),
            EntitySpec(name="云服务商", role=EntityRole.PROCESSOR),
            EntitySpec(name="海外子公司", role=EntityRole.OVERSEAS_RECEIVER),
            EntitySpec(name="用户手机号", role=EntityRole.DATA_CATEGORY, is_sensitive=True),
        ],
        edges=[
            EdgeSpec(
                "电商平台",
                "云服务商",
                EdgeType.ENTRUST,
                EntityRole.CONTROLLER,
                EntityRole.PROCESSOR,
            ),
            EdgeSpec(
                "云服务商",
                "海外子公司",
                EdgeType.CROSS_BORDER,
                EntityRole.PROCESSOR,
                EntityRole.OVERSEAS_RECEIVER,
                is_risk=True,
            ),
            EdgeSpec(
                "电商平台",
                "用户手机号",
                EdgeType.COLLECT,
                EntityRole.CONTROLLER,
                EntityRole.DATA_CATEGORY,
            ),
        ],
    )
    return builder


def test_build_creates_directed_graph():
    """构建有向图：节点数与边数正确。"""
    builder = _build_example()
    g = builder.graph
    assert isinstance(g, nx.DiGraph)
    assert g.number_of_nodes() == 4
    assert g.number_of_edges() == 3


def test_entity_dedup_by_name_role():
    """同 name+role 实体去重（不重复建节点）。"""
    builder = GraphBuilder()
    id1 = builder.add_entity(EntitySpec(name="电商平台", role=EntityRole.CONTROLLER))
    id2 = builder.add_entity(EntitySpec(name="电商平台", role=EntityRole.CONTROLLER))
    assert id1 == id2
    assert builder.graph.number_of_nodes() == 1


def test_edge_dedup_by_from_to_type():
    """同 from+to+type 边去重。"""
    builder = GraphBuilder()
    e1 = EdgeSpec("A", "B", EdgeType.SHARE, EntityRole.CONTROLLER, EntityRole.PROCESSOR)
    e2 = EdgeSpec("A", "B", EdgeType.SHARE, EntityRole.CONTROLLER, EntityRole.PROCESSOR)
    id1 = builder.add_edge(e1)
    id2 = builder.add_edge(e2)
    assert id1 == id2
    assert builder.graph.number_of_edges() == 1


def test_to_payload_contract_fields():
    """GraphPayload 序列化对齐 4.7（camelCase + 枚举值）。"""
    builder = _build_example()
    payload = builder.to_payload().dump_dict()

    # entities：camelCase isSensitive + 枚举角色值
    sensitive_hit = any(
        e["name"] == "用户手机号" and e["role"] == "dataCategory" and e["isSensitive"]
        for e in payload["entities"]
    )
    assert sensitive_hit
    # edges：from 别名 + 枚举 type + isRisk
    cross = [e for e in payload["edges"] if e["type"] == "crossBorder"]
    assert len(cross) == 1
    assert cross[0]["isRisk"] is True
    # 默认字段：riskPaths / suggestions 空列表
    assert payload["riskPaths"] == []
    assert payload["suggestions"] == []
