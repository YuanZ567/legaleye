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
        re.compile(r"(向|共享给|提供给)[^。；]{2,40}(第三方|接收方|境外|子公司|云服务商|合作方|推广方|广告商)"),
        re.compile(r"(接收方|第三方|合作方)[为是][^。；]{2,40}"),
    ],
    DeclarationKey.CROSS_BORDER: [
        re.compile(r"(不向境外|不出境|境内存储|不跨境|向境外|跨境|境外提供)[^。；]{0,30}"),
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
