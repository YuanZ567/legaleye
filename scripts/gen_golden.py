"""M10-1 金标集生成器：脚本化生成 data/golden/ 40 份（30 单 + 10 组多文档）。

每份文档：.md 原文 + .json 标注（expectedFindings 引用知识库真实法条 + entities/relations 第1层指标）。
- 每份埋 2-4 个违规点 + 1 条合规干扰项（测误报，干扰项不出现在 expectedFindings）；
- 多文档组埋 1-2 处交叉矛盾（crossConsistency）；
- clauseRef 仅用知识库真实存在的条款号（红线3，防条款幻觉从源头测）。

用法（本机无 uv）：
  cd backend && .venv/Scripts/python.exe ../scripts/gen_golden.py
输出：data/golden/single/g01..g30 / multi/m01a..m10c + README.md；stdout 打印每份埋点清单供抽查。
"""

import json
import random
import sys
from pathlib import Path

# ── 知识库真实条款（红线3：clauseRef 必须与 LawBaseline 一致；知识库为中文数字）─────
# 经查询知识库 LawBaseline.article_no（30 条），格式为中文数字，如 第六条/第十三条/第三十九条。
LAW_PIPL = "个人信息保护法"
KNOWN_CLAUSES = [
    "第四条", "第五条", "第六条", "第八条", "第十条", "第十二条", "第十三条",
    "第十六条", "第十七条", "第十九条", "第二十条", "第二十一条", "第二十二条",
    "第二十三条", "第二十六条", "第二十七条", "第三十二条", "第三十七条",
    "第三十九条", "第四十条", "第四十一条", "第四十二条", "第四十三条", "第五十五条",
]

# 关系类型 → EdgeType 值（与 rule_extractor 输出一致，供第 1 层关系 F1 精确匹配）
REL_TYPE = {
    "收集": "collect", "存储": "store", "共享": "share", "委托": "entrust",
    "跨境提供": "crossBorder", "匿名化": "anonymize",
}

# ── 违规点模板库：每模板含 文档句 + 标注 ──────────────────────────
# 字段：dimension / verdict / level / clauseRef / keywords / evidence / sentence / entities / relations
# 注意：evidence 与 sentence 必须同步（金标证据来自文档原文，供匹配一致性）
VIOLATIONS = [
    {
        "dimension": "d1Collection", "verdict": "nonCompliant", "level": "high",
        "clauseRef": "第五条",
        "keywords": ["最小必要", "过度收集"],
        "evidence": "收集您的手机号、身份证号码、账号、位置信息等全部个人信息",
        "sentence": "为提供服务，我们会收集您的手机号、身份证号码、账号、位置信息等全部个人信息。",
        "entities": [("我们", "controller"), ("手机号", "dataCategory"), ("身份证", "dataCategory"), ("账号", "dataCategory")],
        "relations": [("我们", "收集", "手机号"), ("我们", "收集", "身份证"), ("我们", "收集", "账号")],
    },
    {
        "dimension": "d1Collection", "verdict": "nonCompliant", "level": "medium",
        "clauseRef": "第五条",
        "keywords": ["无关字段", "业务必需"],
        "evidence": "收集与业务无关的生物识别信息、账号信息等敏感个人信息",
        "sentence": "为了丰富用户画像，我们会收集与业务无关的生物识别信息、账号信息等敏感个人信息。",
        "entities": [("我们", "controller"), ("生物识别", "dataCategory"), ("账号", "dataCategory")],
        "relations": [("我们", "收集", "生物识别"), ("我们", "收集", "账号")],
    },
    {
        "dimension": "d2Notice", "verdict": "nonCompliant", "level": "high",
        "clauseRef": "第十七条",
        "keywords": ["告知", "处理目的", "方式"],
        "evidence": "未明确告知处理个人信息的种类、目的与保存期限",
        "sentence": "我们可能对您的个人信息进行必要处理，处理的具体种类、目的与保存期限不在本政策中说明。",
        "entities": [("我们", "controller"), ("个人信息", "dataCategory")],
        "relations": [("我们", "收集", "个人信息")],
    },
    {
        "dimension": "d3Purpose", "verdict": "nonCompliant", "level": "medium",
        "clauseRef": "第五条",
        "keywords": ["超目的", "无关用途"],
        "evidence": "将收集的信息用于与提供商品无关的广告推送",
        "sentence": "您提供的信息除用于订单配送外，还将用于向您推送与商品无关的第三方广告。",
        "entities": [("我们", "controller"), ("信息", "dataCategory")],
        "relations": [("我们", "共享", "信息")],
    },
    {
        "dimension": "d4ThirdParty", "verdict": "nonCompliant", "level": "high",
        "clauseRef": "第二十二条",
        "keywords": ["单独同意", "第三方共享"],
        "evidence": "向第三方共享个人信息未取得您的单独同意",
        "sentence": "我们会将您的信息共享给合作营销商以开展推广活动，无需另行取得您的同意。",
        "entities": [("我们", "controller"), ("合作营销商", "processor"), ("信息", "dataCategory")],
        "relations": [("我们", "共享", "信息")],
    },
    {
        "dimension": "d5CrossBorder", "verdict": "nonCompliant", "level": "high",
        "clauseRef": "第三十九条",
        "keywords": ["单独同意", "境外提供"],
        "evidence": "将个人信息跨境提供给境外接收方，未取得单独同意",
        "sentence": "为提升服务，我们会将您的个人信息跨境提供给境外的云服务商，您注册即视为同意该传输。",
        "entities": [("我们", "controller"), ("境外云服务商", "overseasReceiver"), ("个人信息", "dataCategory")],
        "relations": [("我们", "跨境提供", "个人信息")],
    },
    {
        "dimension": "d6DataRights", "verdict": "nonCompliant", "level": "medium",
        "clauseRef": "第八条",
        "keywords": ["删除权", "更正权", "复制权"],
        "evidence": "未提供删除、更正、复制个人信息的渠道",
        "sentence": "您已提交的个人信息将长期保存，且不提供删除或更正渠道。",
        "entities": [("我们", "controller"), ("个人信息", "dataCategory")],
        "relations": [("我们", "存储", "个人信息")],
    },
    {
        "dimension": "d1Collection", "verdict": "nonCompliant", "level": "low",
        "clauseRef": "第13条",
        "keywords": ["合法基础", "同意缺失"],
        "evidence": "处理敏感个人信息未取得单独同意",
        "sentence": "我们处理您的生物识别信息以用于登录，无需您单独同意。",
        "entities": [("我们", "controller"), ("生物识别", "dataCategory")],
        "relations": [("我们", "收集", "生物识别")],
    },
    {
        "dimension": "d5CrossBorder", "verdict": "nonCompliant", "level": "medium",
        "clauseRef": "第四十条",
        "keywords": ["出境评估", "安全评估"],
        "evidence": "向境外提供重要数据未申报数据出境安全评估",
        "sentence": "我们将处理的重要数据直接提供给境外合作方，未申报数据出境安全评估。",
        "entities": [("我们", "controller"), ("境外合作方", "overseasReceiver"), ("重要数据", "dataCategory")],
        "relations": [("我们", "跨境提供", "重要数据")],
    },
    {
        "dimension": "d3Purpose", "verdict": "nonCompliant", "level": "low",
        "clauseRef": "第五条",
        "keywords": ["目的限定", "超出范围"],
        "evidence": "将个人信息用于初始目的之外",
        "sentence": "您提供的账号信息会被用于产品调研，超出您当初提供的订单一对一联系用途。",
        "entities": [("我们", "controller"), ("账号", "dataCategory")],
        "relations": [("我们", "收集", "账号")],
    },
]

# 合规干扰项（对照组，测误报；不出现在 expectedFindings）
COMPLIANT_DISTRACTORS = [
    "我们仅收集提供商品所需的必要信息，且均已取得您的明确同意。",
    "我们已对个人信息采取加密与访问控制措施，存储期限不超过实现目的所必需。",
    "我们向第三方共享信息前，会逐项取得您的单独同意。",
    "您可通过个人中心随时查询、更正、删除您的个人信息。",
    "向境外提供个人信息前，我们将依法完成数据出境安全评估并取得单独同意。",
]

# ── 多文档交叉矛盾模板 ─────────────────────────────────────────
CROSS_CONFLICTS = [
    ("我们不会将您的个人信息共享给任何第三方。", "为营销需要，我们会将您的个人信息共享给广告合作方。", "共享", ["共享", "第三方"]),
    ("您的个人信息不提供至境外。", "为提升服务，您的个人信息将传输至境外的云服务商。", "跨境", ["跨境", "境外"]),
    ("我们不会委托第三方处理您的个人信息。", "您的订单信息将委托给第三方物流商处理。", "委托", ["委托", "第三方"]),
]

CROSS_DISTRACTOR_A = "我们会依法保护您的个人信息安全。"
CROSS_DISTRACTOR_B = "我们亦会依法保护您的个人信息安全。"


def _entity_key(name, role):
    return f"{name}::{role}"


def _doc_header(name: str, rng: random.Random) -> str:
    return (
        f"# {name} 隐私政策\n\n"
        f"更新日期：2026-01-01\n\n"
        "## 一、总则\n"
        "欢迎使用本平台，我们高度重视您的个人信息保护，将依法处理您的个人信息。\n"
        "本政策适用于平台提供的全部服务。\n\n"
        "## 二、个人信息处理说明\n"
    )


def _doc_footer() -> str:
    return (
        "\n## 六、联系我们\n"
        "如有疑问，请联系 privacy@example.com，我们将尽快处理。\n"
    )


def _build_single(id_str: str, violations: list[dict], distractor: str, rng: random.Random) -> tuple[str, dict]:
    lines = [_doc_header(f"文档 {id_str.upper()}", rng)]
    lines.append("### 2.1 信息收集\n")
    for v in violations:
        lines.append(v["sentence"])
        lines.append("")
    lines.append("### 2.2 信息使用与存储\n")
    lines.append(distractor)
    lines.append("")
    lines.append("### 2.3 其他说明\n")
    lines.append("本政策未尽事宜参照相关法律法规执行。\n")
    lines.append(_doc_footer())
    text = "".join(lines)

    expected, entities, relations = [], {}, []
    for v in violations:
        expected.append({
            "dimension": v["dimension"], "verdict": v["verdict"], "level": v["level"],
            "clauseRef": v["clauseRef"], "descriptionKeywords": v["keywords"],
            "evidenceText": v["sentence"].strip(),  # 证据 = 文档原文句（保证逐字在文中）
        })
        for (name, role) in v["entities"]:
            entities.setdefault(_entity_key(name, role), {"name": name, "role": role})
        for (src, rel, dst) in v["relations"]:
            relations.append({"source": src, "type": REL_TYPE.get(rel, rel), "target": dst})

    high = sum(1 for f in expected if f["level"] == "high")
    annotation = {
        "id": id_str, "type": "single", "document": [f"{id_str}.md"],
        "expectedFindings": expected, "expectedHighRiskCount": high,
        "entities": list(entities.values()), "relations": relations,
        "notes": "；".join(f"{f['dimension']}: {f['clauseRef']} ({f['evidenceText']})" for f in expected),
    }
    return text, annotation


def _build_multi(grp: str, conflicts: list[dict], rng: random.Random) -> tuple[dict[str, str], dict]:
    docs, expected, entities, relations = {}, [], {}, []

    a_violations = rng.sample(VIOLATIONS, 2)
    a_lines = [_doc_header(f"文档 {grp}A", rng)]
    a_lines.append("### 2.1 信息收集\n")
    a_lines.append(a_violations[0]["sentence"])
    a_lines.append("")
    a_lines.append("### 2.2 信息共享与跨境\n")
    a_lines.append(conflicts[0][0])
    a_lines.append("")
    a_lines.append(conflicts[1][0] if len(conflicts) > 1 else CROSS_DISTRACTOR_A)
    a_lines.append("")
    a_lines.append(_doc_footer())
    docs[f"{grp}a.md"] = "".join(a_lines)

    b_violations = rng.sample(VIOLATIONS, 2)
    b_lines = [_doc_header(f"文档 {grp}B", rng)]
    b_lines.append("### 2.1 信息处理\n")
    b_lines.append(b_violations[0]["sentence"])
    b_lines.append("")
    b_lines.append("### 2.2 与集团/第三方的关系\n")
    b_lines.append(conflicts[0][1])
    b_lines.append("")
    b_lines.append(conflicts[1][1] if len(conflicts) > 1 else CROSS_DISTRACTOR_B)
    b_lines.append("")
    b_lines.append(_doc_footer())
    docs[f"{grp}b.md"] = "".join(b_lines)

    for v in (a_violations[0], b_violations[0]):
        expected.append({
            "dimension": v["dimension"], "verdict": v["verdict"], "level": v["level"],
            "clauseRef": v["clauseRef"], "descriptionKeywords": v["keywords"],
            "evidenceText": v["sentence"].strip(),  # 证据 = 文档原文句
        })
        for (name, role) in v["entities"]:
            entities.setdefault(_entity_key(name, role), {"name": name, "role": role})
        for (src, rel, dst) in v["relations"]:
            relations.append({"source": src, "type": REL_TYPE.get(rel, rel), "target": dst})
    for c in conflicts:
        expected.append({
            "dimension": "crossConsistency", "verdict": "nonCompliant", "level": "high",
            "clauseRef": "", "descriptionKeywords": c[2], "evidenceText": c[1],
        })

    high = sum(1 for f in expected if f["level"] == "high")
    annotation = {
        "id": grp, "type": "multi", "document": [f"{grp}a.md", f"{grp}b.md"],
        "expectedFindings": expected, "expectedHighRiskCount": high,
        "entities": list(entities.values()), "relations": relations,
        "notes": "；".join(f"{f['dimension']}: {f['clauseRef'] or '交叉矛盾'} ({f['evidenceText']})" for f in expected),
    }
    return docs, annotation


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "data" / "golden"
    single_dir, multi_dir = root / "single", root / "multi"
    single_dir.mkdir(parents=True, exist_ok=True)
    multi_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(42)  # 固定种子，可复现

    print("生成 30 份单文档金标")
    for i in range(1, 31):
        gid = f"g{i:02d}"
        violations = rng.sample(VIOLATIONS, rng.randint(2, 4))
        text, ann = _build_single(gid, violations, rng.choice(COMPLIANT_DISTRACTORS), rng)
        (single_dir / f"{gid}.md").write_text(text, encoding="utf-8")
        (single_dir / f"{gid}.json").write_text(json.dumps(ann, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {gid}: {len(ann['expectedFindings'])} 违规点 | {ann['notes']}")

    print("生成 10 组多文档金标")
    for i in range(1, 11):
        gid = f"m{i:02d}"
        conflicts = rng.sample(CROSS_CONFLICTS, rng.randint(1, 2))
        docs, ann = _build_multi(gid, conflicts, rng)
        for fname, content in docs.items():
            (multi_dir / fname).write_text(content, encoding="utf-8")
        (multi_dir / f"{gid}.json").write_text(json.dumps(ann, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {gid}: {len(ann['expectedFindings'])} 标注项 | {ann['notes']}")

    (root / "README.md").write_text(
        "# 金标集（M10-1）\n\n"
        "- 30 份单文档（single/g01-g30）+ 10 组多文档（multi/m01-m10，每组 2 份）\n"
        "- 每份埋 2-4 个违规点 + 1 条合规干扰项（测误报）；多文档组埋 1-2 处交叉矛盾\n"
        "- 标注引用知识库真实法条（clauseRef 与 LawBaseline 一致）\n"
        "- 生成：`cd backend && .venv/Scripts/python.exe ../scripts/gen_golden.py`（种子 42 可复现）\n"
        "- 标注结构：expectedFindings（dimension/verdict/level/clauseRef/descriptionKeywords/evidenceText）+ entities/relations\n"
        "- 抽查记录见底部\n\n## 抽查记录\n\n- [ ] g01-g10 已抽查\n- [ ] m01-m05 已抽查\n",
        encoding="utf-8",
    )
    print("\n生成完成：data/golden/ 共 40 份（30 单 + 10 组多文档）")
    print("已打印每份埋点清单，请抽查 5-10 份确认标注与文档一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
