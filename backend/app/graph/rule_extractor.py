"""规则抽取通道（M3-2）：词典 + 正则，从文档文本提取实体/关系。

- 词典：按角色关键词识别实体（controller/processor/trustee/overseasReceiver/dataCategory）；
- 关系正则：识别 收集/存储/共享/委托/跨境/匿名化 等动作 → EdgeType；
- 输出 EntitySpec / EdgeSpec（供 GraphBuilder 建图；M3-3 LLM 通道并入后做双通道合并）。

纯规则实现，确定性可测；无外部依赖。
"""

import re
from dataclasses import dataclass, field

from app.core.enums import EdgeType, EntityRole
from app.graph.builder import EdgeSpec, EntitySpec

# ── 实体词典：关键词 -> 角色 ──
ENTITY_DICT: dict[EntityRole, tuple[str, ...]] = {
    EntityRole.CONTROLLER: ("处理者", "我方", "平台", "公司", "控制者", "我们"),
    EntityRole.PROCESSOR: ("受托方", "服务商", "云服务商", "供应商", "第三方处理者", "合作方"),
    EntityRole.TRUSTEE: ("托管方", "受托人", "保管方"),
    EntityRole.OVERSEAS_RECEIVER: ("境外接收方", "境外", "海外", "跨境接收", "国外"),
    EntityRole.DATA_CATEGORY: ("个人信息", "手机号", "账号", "身份证", "数据", "信息", "生物识别"),
}

# 敏感数据类别关键词（标记 is_sensitive）
SENSITIVE_KEYWORDS: tuple[str, ...] = (
    "手机号",
    "身份证",
    "生物识别",
    "健康",
    "行踪",
    "敏感个人信息",
)

# ── 关系正则：动作 -> EdgeType ──
# 语义优先级：委托/跨境/共享（强关系）优先于 收集/存储/匿名化（弱/内部处理），
# 保证"委托...存储"这类句子识别为 entrust 而非 store。
RELATION_PATTERNS: list[tuple[re.Pattern, EdgeType]] = [
    (re.compile(r"跨境|向境外|传输到境外|境外提供|出境"), EdgeType.CROSS_BORDER),
    (re.compile(r"委托|委托处理"), EdgeType.ENTRUST),
    (re.compile(r"共享|转让|提供给|披露给"), EdgeType.SHARE),
    (re.compile(r"匿名化|去标识化"), EdgeType.ANONYMIZE),
    (re.compile(r"收集|采集"), EdgeType.COLLECT),
    (re.compile(r"存储|保存|存放"), EdgeType.STORE),
]

# 关系触发词（用于定位关系句）
RELATION_TRIGGER = re.compile(
    r"收集|采集|存储|保存|共享|提供|公开|委托|跨境|向境外|匿名化|去标识化"
)


@dataclass
class RuleExtraction:
    """规则通道抽取结果。"""

    entities: list[EntitySpec] = field(default_factory=list)
    edges: list[EdgeSpec] = field(default_factory=list)

    def dedup(self) -> None:
        """按 (name, role) / (source, target, type) 去重（对齐 M3-1 去重）。"""
        seen_e: set[tuple[str, EntityRole]] = set()
        entities = []
        for e in self.entities:
            if (e.name, e.role) not in seen_e:
                seen_e.add((e.name, e.role))
                entities.append(e)
        self.entities = entities

        seen_edge: set[tuple[str, str, EdgeType]] = set()
        edges = []
        for e in self.edges:
            key = (e.source, e.target, e.edge_type)
            if key not in seen_edge:
                seen_edge.add(key)
                edges.append(e)
        self.edges = edges


def _match_role(name: str) -> EntityRole | None:
    """按词典判断实体名所属角色；无法判断返回 None。"""
    for role, keywords in ENTITY_DICT.items():
        if any(kw in name for kw in keywords):
            return role
    return None


def _is_sensitive(name: str) -> bool:
    return any(kw in name for kw in SENSITIVE_KEYWORDS)


def _split_sentences(text: str) -> list[str]:
    """按句号/分号/换行切句（保留中文语义单元）。"""
    return [s.strip() for s in re.split(r"[。；;\n]", text) if s.strip()]


def extract_by_rules(text: str) -> RuleExtraction:
    """从文本提取实体与关系（规则通道）。"""
    result = RuleExtraction()
    sentences = _split_sentences(text)

    # 1) 句子级识别：定位含关系触发词的句子，提取源/目标实体
    for sent in sentences:
        if not RELATION_TRIGGER.search(sent):
            continue
        # 该句中出现的实体（词典匹配）
        found: dict[str, EntityRole] = {}
        for role, keywords in ENTITY_DICT.items():
            for kw in keywords:
                if kw in sent:
                    found[kw] = role
        if not found:
            continue

        # 确定关系类型（首个命中的动作）
        edge_type = None
        for pattern, etype in RELATION_PATTERNS:
            if pattern.search(sent):
                edge_type = etype
                break
        if edge_type is None:
            continue

        # 源实体：取最长的 controller 关键词（避免"处理者/我们/公司"同义分身）
        controllers = [k for k, r in found.items() if r == EntityRole.CONTROLLER]
        source = max(controllers, key=len) if controllers else next(iter(found))
        source_role = EntityRole.CONTROLLER if controllers else found[source]

        # 目标实体：排除源自身及与源同角色（同义分身）的实体
        targets = [k for k, r in found.items() if k != source and r != source_role]
        if not targets:
            continue

        is_risk = edge_type == EdgeType.CROSS_BORDER  # 跨境默认风险标记（R2 细化）

        result.entities.append(
            EntitySpec(name=source, role=source_role, is_sensitive=_is_sensitive(source))
        )
        for target in targets:
            target_role = found[target]
            result.entities.append(
                EntitySpec(name=target, role=target_role, is_sensitive=_is_sensitive(target))
            )
            result.edges.append(
                EdgeSpec(
                    source=source,
                    target=target,
                    edge_type=edge_type,
                    source_role=source_role,
                    target_role=target_role,
                    is_risk=is_risk,
                )
            )

    result.dedup()
    return result


def extract_with_demo(text: str) -> RuleExtraction:
    """金标 demo 隐私政策文本的抽取入口（M3-2 验收用，等价 extract_by_rules）。"""
    return extract_by_rules(text)
