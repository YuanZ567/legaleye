"""双通道合并器（M3-3）：规则通道 + LLM 通道结果合并。

合并纪律（TODO M3 关键纪律）：
- **冲突保留 LLM**：同实体/同边属性冲突时，采用 LLM 结果，并将该实体/边标记为低置信度；
- 绝不静默覆盖规则：冲突时保留 LLM 但明确标记，供前端/下游感知；
- LLM 独有 / 规则独有均保留。
"""

from dataclasses import dataclass, field

from app.core.enums import EdgeType
from app.graph.builder import EdgeSpec, EntitySpec
from app.graph.llm_extractor import LLMExtraction
from app.graph.rule_extractor import RuleExtraction


@dataclass
class MergedExtraction:
    """合并结果：实体/边 + 低置信度标记。"""

    entities: list[EntitySpec] = field(default_factory=list)
    edges: list[EdgeSpec] = field(default_factory=list)
    # 低置信度实体/边标识：(kind, key)，kind ∈ {entity, edge}
    low_confidence: list[tuple[str, str]] = field(default_factory=list)


def _entity_key(name: str) -> str:
    return name.strip()


def _edge_key(source: str, target: str, etype: EdgeType) -> str:
    return f"{source.strip()}::{target.strip()}::{etype.value}"


def merge_channels(rule: RuleExtraction, llm: LLMExtraction) -> MergedExtraction:
    """合并规则与 LLM 抽取结果。

    实体冲突（同 name 角色不同）→ 保留 LLM 角色，标低置信；
    边冲突（同 source+target+type 属性不同）→ 保留 LLM，标低置信。
    """
    merged = MergedExtraction()

    # ── 实体合并 ──
    rule_entities: dict[str, EntitySpec] = {}
    for e in rule.entities:
        rule_entities[_entity_key(e.name)] = e
    llm_entities: dict[str, EntitySpec] = {}
    for e in llm.entities:
        llm_entities[_entity_key(e.name)] = e

    all_names = set(rule_entities) | set(llm_entities)
    for name in all_names:
        r = rule_entities.get(name)
        llm_e = llm_entities.get(name)
        if llm_e is not None:
            # LLM 存在：若规则也命中且角色冲突，保留 LLM 角色 + 标低置信
            chosen = llm_e
            if r is not None and r.role != llm_e.role:
                merged.low_confidence.append(("entity", name))
        else:
            # 仅规则命中：保留规则
            chosen = r
        merged.entities.append(chosen)

    # ── 边合并 ──
    rule_edges: dict[str, EdgeSpec] = {}
    for e in rule.edges:
        rule_edges[_edge_key(e.source, e.target, e.edge_type)] = e
    llm_edges: dict[str, EdgeSpec] = {}
    for e in llm.edges:
        llm_edges[_edge_key(e.source, e.target, e.edge_type)] = e

    all_edge_keys = set(rule_edges) | set(llm_edges)
    for key in all_edge_keys:
        re_ = rule_edges.get(key)
        le_ = llm_edges.get(key)
        if le_ is not None:
            # LLM 存在：若规则也命中且属性冲突，保留 LLM + 标低置信
            chosen = le_
            if re_ is not None and (
                re_.legal_basis != le_.legal_basis or re_.is_risk != le_.is_risk
            ):
                merged.low_confidence.append(("edge", key))
        else:
            chosen = re_
        merged.edges.append(chosen)

    # 实体冲突未发生时也补角色对齐：边的端点角色按实体合并后的角色回填（由调用方在建图时处理）
    return merged
