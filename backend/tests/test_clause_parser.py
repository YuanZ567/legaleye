"""M2-2 验收测试：条款结构化解析器（章节/条/款）。

- 支持中文数字与阿拉伯数字的 `第X条` / `第X条第X款`；
- clauseRef 输出兼容 DATA_CONTRACT 3.2 正则；
- 金标法条样例（个人信息保护法结构）拆分正确率 100%。
"""

import re

from app.knowledge.clause_parser import (
    cn_to_int,
    cn_to_int_inv,
    parse_clause_ref,
    split_into_clauses,
)

# DATA_CONTRACT 3.2 clauseRef 正则（测试用）
CLAUSE_REF_RE = re.compile(r"第?[一二三四五六七八九十\d]+条(第[一二三四五六七八九十\d]+款)?")


# ── 中文数字转换 ──


def test_cn_to_int():
    assert cn_to_int("一") == 1
    assert cn_to_int("十") == 10
    assert cn_to_int("十一") == 11
    assert cn_to_int("二十") == 20
    assert cn_to_int("三十五") == 35
    assert cn_to_int("一百零五") == 105
    assert cn_to_int("99") == 99


def test_cn_to_int_inv():
    assert cn_to_int_inv(1) == "一"
    assert cn_to_int_inv(10) == "十"
    assert cn_to_int_inv(21) == "二十一"
    assert cn_to_int_inv(35) == "三十五"


# ── 单条 clauseRef 解析 ──


def test_parse_clause_ref_basic():
    c = parse_clause_ref("第十条")
    assert c is not None and c.article == 10 and c.clause is None
    assert c.article_no == "第十条"


def test_parse_clause_ref_with_clause():
    c = parse_clause_ref("第十条第一款")
    assert c is not None and c.article == 10 and c.clause == 1


def test_parse_clause_ref_arabic():
    c = parse_clause_ref("第12条第二款")
    assert c is not None and c.article == 12 and c.clause == 2


def test_parse_clause_ref_invalid():
    assert parse_clause_ref("本节") is None
    assert parse_clause_ref("附录") is None


def test_clause_ref_matches_contract_regex():
    for ref in ["第一条", "第十条", "第10条", "第三十八条第二款", "第55条第三款"]:
        assert CLAUSE_REF_RE.fullmatch(ref), f"{ref} 不匹配契约正则"


# ── 金标法条拆分（个人信息保护法结构样例）──


_GOLD = """
第一章　总　则
第一条　为了保护个人信息权益，规范个人信息处理活动，促进个人信息合理利用，制定本法。
第二条　在中华人民共和国境内处理自然人个人信息的活动，适用本法。
第四条　个人信息是以电子或者其他方式记录的与已识别或者可识别的自然人有关的各种信息。
第二十六条　个人信息处理者处理个人信息，应当遵循合法、正当、必要和诚信原则。
第二十七条　个人信息处理者可以依照本法规定处理个人信息：
第一款　取得个人的同意；
第二款　为订立、履行个人作为一方当事人的合同所必需；
第三款　为履行法定职责或者法定义务所必需。
"""


def test_gold_split_all_articles():
    """金标法条：所有条均被识别，条号正确。"""
    clauses = split_into_clauses(_GOLD)
    articles = [c.article for c in clauses if not c.is_clause]
    assert articles == [1, 2, 4, 26, 27], f"解析条号错误: {articles}"


def test_gold_split_clauses():
    """金标法条：第27条的款被正确拆分。"""
    clauses = split_into_clauses(_GOLD)
    # 第27条下应有三款
    clause_items = [c for c in clauses if c.article == 27 and c.is_clause]
    assert [c.clause for c in clause_items] == [1, 2, 3]


def test_gold_all_refs_match_contract():
    """金标法条：所有 clauseRef 均匹配契约正则。"""
    clauses = split_into_clauses(_GOLD)
    assert clauses, "未解析出任何条款"
    for c in clauses:
        assert CLAUSE_REF_RE.fullmatch(c.ref), f"{c.ref} 不匹配契约正则"


def test_gold_accuracy_100_percent():
    """金标法条抽查：解析正确率 100%（条号/款号/章节对齐）。"""
    clauses = split_into_clauses(_GOLD, statute="个人信息保护法", chapter=1)
    # 全部条款应归属第一章
    assert all(c.chapter == 1 for c in clauses)
    # 主条款：第一条/第二条/第四条/第二十六条/第二十七条
    main = [c for c in clauses if not c.is_clause]
    assert len(main) == 5
    # 款子句：3 款
    sub = [c for c in clauses if c.is_clause]
    assert len(sub) == 3
    # 总数 = 5 条 + 3 款 = 8
    assert len(clauses) == 8
    # 校验具体条款文本非空且无遗漏
    texts = {c.article: c.text for c in main}
    assert "保护个人信息权益" in texts[1]
    assert "合法、正当、必要" in texts[26]
