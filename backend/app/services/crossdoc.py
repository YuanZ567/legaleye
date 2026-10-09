"""跨文档联合审查服务（M6）：声明键抽取 + 对齐比对 + 矛盾判定。

- 6 个声明键（DATA_CONTRACT 4.8 DeclarationKey）：dataCategory/purpose/receivers/
  crossBorder/retention/rights；
- 声明键抽取用规则（词典+正则）确定性实现；
- 对齐比对 + 名称归一化（M6-2）；
- 矛盾级别判定（高/中/低）+ 双方原文证据（M6-3）。

跨文档联合审查复用 M4 工作流模式，区别在 documents 字段是数组而非单文件。
"""

import re
from dataclasses import dataclass

from app.core.enums import DeclarationKey, RiskLevel

# ── 各声明键的抽取正则（定位原文证据） ──
KEY_PATTERNS: dict[DeclarationKey, list[re.Pattern]] = {
    DeclarationKey.DATA_CATEGORY: [
        re.compile(r"收集[^。；]*?(手机号|账号|身份证|生物识别|健康|个人信息|数据)"),
        re.compile(r"(手机号|账号|身份证|生物识别|健康|个人信息)等?(信息|数据)"),
        re.compile(r"数据类别(包括|为|：)[^。；]{2,40}"),
    ],
    DeclarationKey.PURPOSE: [
        re.compile(r"用于[^。；]{2,40}"),
        re.compile(r"(处理|使用)目的[是为]?[^。；]{2,40}"),
    ],
    DeclarationKey.RECEIVERS: [
        # 从句子开头匹配，保留否定前缀（"不会将…共享给" 归为否定句）
        re.compile(r"[^。；]*?(共享给|提供给|提供|委托给|委托|不共享|不委托|不向|不提供|向)[^。；]{0,40}(第三方|接收方|境外|子公司|云服务商|合作方|推广方|广告商|物流商)"),
        re.compile(r"(接收方|第三方|合作方)[为是][^。；]{2,40}"),
    ],
    DeclarationKey.CROSS_BORDER: [
        re.compile(r"[^。；]*?(不向境外|不出境|不跨境|不提供至境外|境内存储|向境外|传输至境外|提供至境外|跨境|境外提供|至境外)[^。；]{0,30}"),
    ],
    DeclarationKey.RETENTION: [
        re.compile(r"(保存|保留|存储)[^。；]{0,10}(?:期限|时间)[^。；]{0,20}(年|月|日|天)"),
        re.compile(r"(?:保存|保留)(\d+)(?:年|月|日|天)[^。；]{0,10}"),
    ],
    DeclarationKey.RIGHTS: [
        re.compile(r"(有权|可以)[^。；]{0,15}(查询|复制|更正|删除|撤回|注销)[^。；]{0,20}"),
    ],
}

# 名称归一化映射（M6-2："境外"/"海外"/"overseas" → 同一概念）
NORMALIZE_MAP: dict[str, str] = {
    "境外": "境外",
    "海外": "境外",
    "国外": "境外",
    "overseas": "境外",
    "cross-border": "跨境",
    "跨境": "跨境",
    "子公司": "子公司",
    "分公司": "子公司",
}


@dataclass
class Declaration:
    """一条声明键的抽取结果。"""

    key: DeclarationKey
    value: str
    text: str  # 原文证据
    char_range: tuple[int, int] | None = None  # 证据在原文的起止位置


def normalize_name(name: str) -> str:
    """名称归一化（M6-2）：同义词映射到统一概念；无法映射返回原文小写。"""
    for alias, canonical in NORMALIZE_MAP.items():
        if alias in name:
            return canonical
    return name.strip().lower()


def extract_declarations(text: str) -> dict[DeclarationKey, Declaration]:
    """从文档文本抽取 6 类声明键（值 + 原文证据）。

    每键取首个命中正则；无命中则不产出该键（value 为空）。
    """
    result: dict[DeclarationKey, Declaration] = {}
    for key, patterns in KEY_PATTERNS.items():
        for pattern in patterns:
            m = pattern.search(text)
            if m:
                evidence_text = m.group(0)
                result[key] = Declaration(
                    key=key,
                    value=normalize_name(evidence_text),
                    text=evidence_text,
                    char_range=(m.start(), m.end()),
                )
                break
    return result


# 否定/不出境表达（用于多声明集合对比）
NEGATIVE_KW = (
    "不共享",
    "不会将",
    "不会向",
    "不向",
    "不提供",
    "不出境",
    "不跨境",
    "境内存储",
    "不会",
    "不委托",
)


def extract_declaration_sets(text: str) -> dict[DeclarationKey, list[str]]:
    """M6 多声明提取：每键收集**所有**命中的声明句（不限于首个）。

    修复点：单文档可能有多条 receivers/crossBorder 声明（如"不共享"+"跨境提供"），
    只取首个会漏掉矛盾（m01: A"不会共享给第三方" vs B"共享给广告合作方"）。
    """
    result: dict[DeclarationKey, list[str]] = {}
    for key, patterns in KEY_PATTERNS.items():
        hits: list[str] = []
        for pattern in patterns:
            hits.extend(m.group(0).strip() for m in pattern.finditer(text))
        if hits:
            result[key] = hits
    return result


def declaration_sets_conflict(a_hits: list[str], b_hits: list[str]) -> bool:
    """多声明集合对比：一侧否定声明、另一侧肯定声明 → 矛盾。

    覆盖金标 multi 矛盾模式：共享（"不会共享" vs "共享给广告合作方"）、
    委托（"不委托" vs "委托给第三方物流商"）、跨境（"不出境" vs "传输至境外"）。
    """
    if not a_hits or not b_hits:
        return False
    a_neg = [h for h in a_hits if any(k in h for k in NEGATIVE_KW)]
    b_neg = [h for h in b_hits if any(k in h for k in NEGATIVE_KW)]
    a_pos = [h for h in a_hits if not any(k in h for k in NEGATIVE_KW)]
    b_pos = [h for h in b_hits if not any(k in h for k in NEGATIVE_KW)]
    # 一侧明确否定、另一侧明确肯定 → 矛盾
    if a_neg and b_pos:
        return True
    if b_neg and a_pos:
        return True
    return False


def _value_is_negative(value: str) -> bool:
    """声明值是否为否定/不出境表达（crossBorder 键专用）。"""
    return any(kw in value for kw in ("不向境外", "不出境", "境内存储", "不跨境"))


def _declaration_sentiment(decl: Declaration) -> str:
    """声明语义倾向：positive（有出境/有收集）/ negative（无出境/不出境）。"""
    if decl.key == DeclarationKey.CROSS_BORDER:
        return "negative" if _value_is_negative(decl.value) else "positive"
    return "positive" if decl.value else "empty"


def compare_declarations(a: Declaration, b: Declaration, *, doc_a: object, doc_b: object) -> bool:
    """M6-2/3 判定两份文档同一声明键是否矛盾。

    简化规则（M6 骨架）：
    - crossBorder：一侧"不出境"、另一侧"出境" → 高矛盾；
    - 其他键：归一化后值差异较大 → 中/低矛盾（值精确不一致即视为矛盾）。
    返回是否构成矛盾。
    """
    if a.key != b.key:
        return False
    if a.key == DeclarationKey.CROSS_BORDER:
        return _declaration_sentiment(a) != _declaration_sentiment(b)
    return normalize_name(a.value) != normalize_name(b.value)


def judge_conflict_level(a: Declaration, b: Declaration) -> RiskLevel:
    """矛盾级别判定：crossBorder 语义冲突 → 高；其余值不一致 → 中。"""
    if a.key == DeclarationKey.CROSS_BORDER:
        return RiskLevel.HIGH
    return RiskLevel.MEDIUM
