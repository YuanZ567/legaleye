"""规则抽取通道：词典 + 正则，从文档文本提取实体/关系。

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
# M10 双语：英文关键词用 \b 词边界正则匹配（_kw_in_sentence），避免子串误命中
# （如 "we" 命中 "answer"）。中文关键词仍用子串匹配。
ENTITY_DICT: dict[EntityRole, tuple[str, ...]] = {
    EntityRole.CONTROLLER: (
        "处理者", "我方", "平台", "公司", "控制者", "我们",
        # EN
        "we", "our", "the company", "data controller",
    ),
    EntityRole.PROCESSOR: (
        "受托方", "服务商", "云服务商", "供应商", "第三方处理者", "合作方",
        # EN
        "service provider", "processor", "vendor", "supplier", "third party",
    ),
    EntityRole.TRUSTEE: (
        "托管方", "受托人", "保管方",
        # EN
        "trustee", "custodian",
    ),
    EntityRole.OVERSEAS_RECEIVER: (
        "境外接收方", "境外", "海外", "跨境接收", "国外",
        # EN
        "overseas recipient", "foreign recipient", "overseas", "foreign",
        "abroad", "international", "outside the country", "outside of the country",
        "outside the eea", "united states", "other countries",
    ),
    EntityRole.DATA_CATEGORY: (
        "个人信息", "手机号", "账号", "身份证", "数据", "信息", "生物识别",
        # EN
        "personal information", "personal data", "phone number",
        "identity card", "ID number", "biometric", "data", "information",
    ),
}

# 敏感数据类别关键词（标记 is_sensitive）
SENSITIVE_KEYWORDS: tuple[str, ...] = (
    "手机号",
    "身份证",
    "生物识别",
    "健康",
    "行踪",
    "敏感个人信息",
    # EN
    "phone number",
    "identity card",
    "biometric",
    "health",
    "location data",
    "sensitive personal",
)

# ── 关系正则：动作 -> EdgeType ──
# 语义优先级：委托/跨境/共享（强关系）优先于 收集/存储/匿名化（弱/内部处理），
# 保证"委托...存储"这类句子识别为 entrust 而非 store。
RELATION_PATTERNS: list[tuple[re.Pattern, EdgeType]] = [
    (re.compile(r"跨境|向境外|传输到境外|境外提供|出境"), EdgeType.CROSS_BORDER),
    # EN cross-border：transfer 与 abroad/overseas 同句才算跨境，普通 transfer 归 share
    (
        re.compile(
            r"cross[- ]?border|outside (?:of )?(?:the )?(?:eea|country|region)|"
            r"transfer(?:s|red|ring)?[^.;]{0,40}(?:abroad|overseas|foreign|outside)|"
            r"(?:abroad|overseas)[^.;]{0,40}transfer",
            re.IGNORECASE,
        ),
        EdgeType.CROSS_BORDER,
    ),
    (re.compile(r"委托|委托处理"), EdgeType.ENTRUST),
    (re.compile(r"on behalf of|entrust(?:s|ed|ing)?", re.IGNORECASE), EdgeType.ENTRUST),
    (re.compile(r"共享|转让|提供给|披露给"), EdgeType.SHARE),
    (
        re.compile(
            r"shar(?:e|es|ed|ing)|disclos(?:e|es|ed|ing)|sell(?:s|ing)?|"
            r"transfer(?:s|red|ring)?|provid(?:e|es|ed|ing)",
            re.IGNORECASE,
        ),
        EdgeType.SHARE,
    ),
    (re.compile(r"匿名化|去标识化"), EdgeType.ANONYMIZE),
    (
        re.compile(r"anonymiz(?:e|es|ed|ing)|de[- ]?identif(?:y|ies|ied)|pseudonymiz(?:e|es|ed|ing)", re.IGNORECASE),
        EdgeType.ANONYMIZE,
    ),
    (re.compile(r"收集|采集"), EdgeType.COLLECT),
    (
        re.compile(r"collect(?:s|ed|ing)?|gather(?:s|ed|ing)?|obtain(?:s|ed|ing)?", re.IGNORECASE),
        EdgeType.COLLECT,
    ),
    (re.compile(r"存储|保存|存放"), EdgeType.STORE),
    (
        re.compile(r"stor(?:e|es|ed|ing)|retain(?:s|ed|ing)?", re.IGNORECASE),
        EdgeType.STORE,
    ),
]

# 关系触发词（用于定位关系句）
RELATION_TRIGGER = re.compile(
    r"收集|采集|存储|保存|共享|提供|公开|委托|跨境|向境外|匿名化|去标识化"
    r"|collect|gather|obtain|stor|retain|shar|disclos|transfer|provid|sell"
    r"|entrust|cross[- ]?border|abroad|overseas|anonymiz|de[- ]?identif|pseudonymiz",
    re.IGNORECASE,
)

_ASCII_KW_CACHE: dict[str, re.Pattern] = {}


def _kw_in_sentence(sent: str, kw: str) -> bool:
    """关键词句子匹配：英文用 \b 词边界（忽略大小写），中文用子串。"""
    if all(ord(c) < 128 for c in kw):
        pat = _ASCII_KW_CACHE.get(kw)
        if pat is None:
            pat = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            _ASCII_KW_CACHE[kw] = pat
        return pat.search(sent) is not None
    return kw in sent


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
    return any(_kw_in_sentence(name, kw) for kw in SENSITIVE_KEYWORDS)


def _split_sentences(text: str) -> list[str]:
    """按句号/分号/换行切句（保留中文语义单元；M10 双语：英文句号 . ! ? 也切分）。"""
    return [s.strip() for s in re.split(r"[。；;.!?\n]", text) if s.strip()]


def extract_by_rules(text: str) -> RuleExtraction:
    """从文本提取实体与关系（规则通道）。"""
    result = RuleExtraction()
    sentences = _split_sentences(text)

    # 1) 句子级识别：定位含关系触发词的句子，提取源/目标实体
    for sent in sentences:
        if not RELATION_TRIGGER.search(sent):
            continue
        # 该句中出现的实体（词典匹配；英文词边界 / 中文子串）
        found: dict[str, EntityRole] = {}
        for role, keywords in ENTITY_DICT.items():
            for kw in keywords:
                if _kw_in_sentence(sent, kw):
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

        # 源实体：取最长的 controller 关键词（避免"处理者/我们/公司"同义分身）；
        # 无 controller 但同时命中 数据类别 + 境外接收方（典型跨境句，如
        # "personal data may be transferred outside the country"）→
        # 以数据实体为主语连向境外接收方（保证 R2 跨境风险路径可达）。
        controllers = [k for k, r in found.items() if r == EntityRole.CONTROLLER]
        overseas_kw = [k for k, r in found.items() if r == EntityRole.OVERSEAS_RECEIVER]
        if controllers:
            source = max(controllers, key=len)
            source_role = EntityRole.CONTROLLER
            # 目标实体：排除源自身及与源同角色（同义分身）的实体
            targets = [k for k, r in found.items() if k != source and r != source_role]
        elif overseas_kw and edge_type == EdgeType.CROSS_BORDER:
            data_kw = [k for k, r in found.items() if r == EntityRole.DATA_CATEGORY]
            if not data_kw:
                continue
            source = data_kw[0]
            source_role = EntityRole.DATA_CATEGORY
            targets = overseas_kw
        else:
            source = next(iter(found))
            source_role = found[source]
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
