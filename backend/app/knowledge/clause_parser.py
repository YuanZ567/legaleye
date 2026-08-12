"""条款结构化解析器（M2-2）：将法条全文拆分为 `第X章 / 第X条 / 第X款` 结构。

对齐 DATA_CONTRACT 3.2 clauseRef 正则：
`第?[一二三四五六七八九十\\d]+条(第[一二三四五六七八九十\\d]+款)?`。

能力：
- 识别章节（第X章）、条（第X条）、款（第X款），支持中文数字与阿拉伯数字混用；
- 生成规范的 clauseRef（保留"第X条（第X款）"原文形式，兼容契约正则）；
- 中文数字 → 阿拉伯数字转换（用于排序/检索键）。

本模块为纯函数工具，不访问 DB（ARCHITECTURE 红线）。
"""

import re
from dataclasses import dataclass

# ── 正则（与 DATA_CONTRACT 3.2 clauseRef 对齐，支持中文数字与阿拉伯数字） ──
_CN_NUM = "一二三四五六七八九十百零〇"
_NUM = rf"[{_CN_NUM}\d]+"
_ARTICLE_RE = re.compile(rf"第({_NUM})条")
_CLAUSE_RE = re.compile(rf"第({_NUM})款")
_CHAPTER_RE = re.compile(rf"第({_NUM})章")

# 中文数字 → 数值（支持一~百内的组合，含零）
_CN_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "百": 100,
}


def cn_to_int(text: str) -> int | None:
    """将中文数字/阿拉伯数字串转为 int；无法解析返回 None。

    支持：'一'~'九'、'十'/'十一'/'二十'/'一百零五' 及纯阿拉伯。
    """
    if text.isdigit():
        return int(text)
    total = 0
    section = 0
    for ch in text:
        if ch in "零〇":
            continue
        if ch in "十百":
            base = _CN_DIGITS[ch]
            total += (section or 1) * base
            section = 0
        elif ch in _CN_DIGITS:
            section = _CN_DIGITS[ch]
    total += section
    return total if total > 0 else None


@dataclass
class Clause:
    """一条结构化条款。"""

    article_no: str  # 规范 clauseRef 格式，如 '第十条' 或 '第十条第一款'
    article: int  # 阿拉伯条号
    clause: int | None  # 阿拉伯款号（无款时为 None）
    chapter: int | None  # 所属章（阿拉伯，无章时为 None）
    text: str  # 该条/款对应的原文文本
    is_clause: bool  # True=第X款；False=第X条（整条）

    @property
    def ref(self) -> str:
        """完整 clauseRef（契约正则格式）。

        注意：款子句的 article_no 构造时已含 '第X款'（如 '第二十七条第一款'），
        此处直接返回，避免重复追加。
        """
        return self.article_no


_CN_LIST = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
_CN_TENS = ["", "十", "二十", "三十", "四十", "五十", "六十", "七十", "八十", "九十"]


def cn_to_int_inv(value: int) -> str:
    """阿拉伯数字 → 中文数字（1~99 内）。"""
    if value <= 9:
        return _CN_LIST[value]
    tens, ones = divmod(value, 10)
    s = _CN_TENS[tens]
    if ones:
        s += _CN_LIST[ones]
    return s


def parse_clause_ref(ref: str) -> Clause | None:
    """解析单个 clauseRef（如 '第十条' / '第十条第一款' / '第12条'）。

    返回 Clause（text 为空，仅结构）；无法解析返回 None。
    """
    m = _ARTICLE_RE.search(ref)
    if not m:
        return None
    article = cn_to_int(m.group(1))
    if article is None:
        return None
    clause = None
    cm = _CLAUSE_RE.search(ref, m.end())
    if cm:
        clause = cn_to_int(cm.group(1))
    # 尽量识别章节
    chapter = None
    chm = _CHAPTER_RE.search(ref[: m.start()])
    if chm:
        chapter = cn_to_int(chm.group(1))
    return Clause(
        article_no=m.group(0),
        article=article,
        clause=clause,
        chapter=chapter,
        text="",
        is_clause=clause is not None,
    )


def split_into_clauses(text: str, *, statute: str = "", chapter: int | None = None) -> list[Clause]:
    """将法条全文拆分为结构化条款列表（M2-3 ingest 用）。

    按 `第X条` 分段；段内若含 `第X款` 则进一步拆分出款子句。
    条款号规范为原文（如 第十条），保留中文数字原始形式以匹配契约。
    """
    # 按 第X条 切分（保留分隔符）
    parts = re.split(rf"(?=第{_NUM}条)", text)
    clauses: list[Clause] = []
    current_chapter = chapter

    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = _ARTICLE_RE.search(part)
        if not m:
            # 无条号文本（如章标题或前导），跳过——由 ingest 层按章关联
            continue
        article = cn_to_int(m.group(1))
        if article is None:
            continue
        # 该条内部按 第X款 再切分
        sub = re.split(rf"(?=第{_NUM}款)", part[m.end() :])
        # 第一款文本是整条的起始部分（不含后续"第X款"）
        body_start = sub[0].strip() if sub else ""
        if not body_start:
            continue
        # 主条款（无款）：记录条号后的正文（不含各款子句）
        clauses.append(
            Clause(
                article_no=m.group(0),
                article=article,
                clause=None,
                chapter=current_chapter,
                text=body_start,
                is_clause=False,
            )
        )
        # 款子句：从第二段起，每段为 第X款 + 内容
        for _i, seg in enumerate(sub[1:], start=1):
            seg = seg.strip()
            if not seg:
                continue
            cm = _CLAUSE_RE.search(seg)
            if not cm:
                continue
            clause_num = cn_to_int(cm.group(1))
            if clause_num is None:
                continue
            clauses.append(
                Clause(
                    article_no=f"{m.group(0)}{cm.group(0)}",
                    article=article,
                    clause=clause_num,
                    chapter=current_chapter,
                    text=seg.strip(),
                    is_clause=True,
                )
            )
    return clauses
