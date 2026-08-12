"""图谱构建器（M3-1）：从实体/边数据构建 networkx 有向图并序列化为契约。

- 实体去重：同 name+role 合并（保留首个 id）；
- 边去重：同 from+to+type 合并（保留首个 id）；
- 序列化为 DATA_CONTRACT 4.7 GraphPayload（entities/edges/riskPaths/suggestions）。

R1-R4 推理（M3-4）在图结构上执行。
"""

import uuid
from dataclasses import dataclass

import networkx as nx

from app.core.enums import EdgeType, EntityRole
from app.schemas.graph import GraphEdge, GraphEntity, GraphPayload


@dataclass
class EntitySpec:
    """实体输入（抽取通道产物）。"""

    name: str
    role: EntityRole
    is_sensitive: bool = False


@dataclass
class EdgeSpec:
    """边输入（抽取通道产物）：引用实体名，需先 add_entity 建好实体。"""

    source: str  # 源实体名
    target: str  # 目标实体名
    edge_type: EdgeType
    source_role: EntityRole  # 源实体角色（未建实体时用此创建）
    target_role: EntityRole  # 目标实体角色
    legal_basis: str | None = None
    is_risk: bool = False


class GraphBuilder:
    """从 EntitySpec/EdgeSpec 构建有向图并输出 GraphPayload。"""

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()
        self._entity_ids: dict[tuple[str, EntityRole], uuid.UUID] = {}  # (name, role) -> id
        self._edge_ids: dict[tuple[uuid.UUID, uuid.UUID, EdgeType], uuid.UUID] = {}

    def add_entity(self, spec: EntitySpec) -> uuid.UUID:
        """加入实体（去重：同 name+role 合并，返回实体 id）。"""
        key = (spec.name, spec.role)
        if key in self._entity_ids:
            return self._entity_ids[key]
        entity_id = uuid.uuid4()
        self._entity_ids[key] = entity_id
        self._graph.add_node(
            entity_id, name=spec.name, role=spec.role, is_sensitive=spec.is_sensitive
        )
        return entity_id

    def _entity_id(self, name: str, role: EntityRole) -> uuid.UUID:
        """获取实体 id；若该 name+role 未建实体，自动创建。"""
        key = (name, role)
        if key not in self._entity_ids:
            return self.add_entity(EntitySpec(name=name, role=role))
        return self._entity_ids[key]

    def add_edge(self, spec: EdgeSpec) -> uuid.UUID:
        """加入边（去重：同 from+to+type 合并，返回边 id）。"""
        src_id = self._entity_id(spec.source, spec.source_role)
        tgt_id = self._entity_id(spec.target, spec.target_role)
        key = (src_id, tgt_id, spec.edge_type)
        if key in self._edge_ids:
            return self._edge_ids[key]
        edge_id = uuid.uuid4()
        self._edge_ids[key] = edge_id
        self._graph.add_edge(
            src_id,
            tgt_id,
            id=edge_id,
            type=spec.edge_type,
            legal_basis=spec.legal_basis,
            is_risk=spec.is_risk,
        )
        return edge_id

    def build(self, entities: list[EntitySpec], edges: list[EdgeSpec]) -> nx.DiGraph:
        """从实体与边数据构建图。"""
        for spec in entities:
            self.add_entity(spec)
        for spec in edges:
            self.add_edge(spec)
        return self._graph

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    def to_payload(self) -> GraphPayload:
        """序列化为契约 GraphPayload。"""
        nodes = sorted(self._graph.nodes(data=True), key=lambda n: n[1]["name"])
        entities = [
            GraphEntity(
                id=nid,
                name=data["name"],
                role=data["role"],
                is_sensitive=data.get("is_sensitive", False),
            )
            for nid, data in nodes
        ]
        edges = [
            GraphEdge(
                id=data["id"],
                from_=str(u),
                to=str(v),
                type=data["type"],
                legal_basis=data.get("legal_basis"),
                is_risk=data.get("is_risk", False),
            )
            for u, v, data in self._graph.edges(data=True)
        ]
        return GraphPayload(entities=entities, edges=edges)
