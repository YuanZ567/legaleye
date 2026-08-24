"""M10-2 三层评估：读金标集 → 复用真实审查链路 → 算三层指标 → 生成报告。

用法（本机无 uv）：
  cd backend && .venv/Scripts/python.exe ../scripts/evaluate.py [--limit N] [--model MODEL]
- --limit N：只跑前 N 份（先 5 份验证管线，再全量 40）
- --model：LLM 模型名，默认 qwen3.7-plus（flash 免费额度已用尽，禁 flash）

红线（M10 重建）：
- 报告数字由脚本真实计算生成（eval_report.md 与 eval_results.json 同源，禁手工改数）；
- 指标口径/阈值硬编码，不可改；
- evaluate.py 只读复用 agent 链（build_workflow + rule_extractor），不改 workflow/factory。

三层指标（阈值）：
  实体 F1≥0.85 / 关系 F1≥0.80 / 高风险召回≥0.90 / 误报率≤0.15 / 条款引用准确率≥0.85 / 交叉矛盾检出率≥0.80
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "data" / "golden"
DEFAULT_MODEL = "qwen3.7-plus"

# 确保可 import 后端 agent 链
_BACKEND = ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# 验收阈值（红线1：不可改）
THRESHOLDS = {
    "entity_f1": 0.85,
    "relation_f1": 0.80,
    "high_risk_recall": 0.90,
    "false_positive_rate": 0.15,
    "clause_accuracy": 0.85,
    "conflict_detection": 0.80,
}


# ── 第 1 层：实体/关系抽取（复用 M3 规则链路，确定性）────────────────
def extract_graph(text: str):
    from app.graph.rule_extractor import extract_by_rules

    result = extract_by_rules(text)
    entities = [
        {"name": e.name, "role": e.role.value if hasattr(e.role, "value") else str(e.role)}
        for e in result.entities
    ]
    relations = [
        {
            "source": e.source,
            "type": e.edge_type.value if hasattr(e.edge_type, "value") else str(e.edge_type),
            "target": e.target,
        }
        for e in result.edges
    ]
    return entities, relations


def _entity_hit(gold: dict, extracted: list[dict]) -> bool:
    for ex in extracted:
        if ex.get("role") == gold.get("role") and (
            gold.get("name") in ex.get("name", "") or ex.get("name") in gold.get("name", "")
        ):
            return True
    return False


def _relation_hit(gold: dict, extracted: list[dict]) -> bool:
    for ex in extracted:
        if ex.get("type") != gold.get("type"):
            continue
        src_hit = gold.get("source") in ex.get("source", "") or ex.get("source") in gold.get("source", "")
        dst_hit = gold.get("target") in ex.get("target", "") or ex.get("target") in gold.get("target", "")
        if src_hit and dst_hit:
            return True
    return False


def _f1(gold_list: list[dict], extracted: list[dict], matcher) -> float:
    """基于金标集的 F1（recall 主导：金标为应识别集合）。"""
    if not gold_list:
        return 1.0
    tp = sum(1 for g in gold_list if matcher(g, extracted))
    fp = max(0, len(extracted) - tp)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / len(gold_list)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ── 第 2/3 层：运行真实审查工作流 ────────────────────────────────
async def _async_run_workflow(text: str, model: str) -> list[dict]:
    from app.agents.workflow import build_workflow

    def make_llm(mdl: str):
        import asyncio as _asyncio

        from app.core.db import SessionLocal
        from app.core.enums import Provider
        from app.llm.factory import chat_completion

        async def llm_func(messages, dimension=None, task_id=None, **kw):
            with SessionLocal() as db:
                return await _asyncio.to_thread(
                    chat_completion,
                    db=db, provider=Provider.BAILIAN, model=mdl,
                    messages=messages, node=dimension, task_id=task_id,
                )

        return llm_func

    agent_fns = {dim: make_llm(model) for dim in ("d1", "d2", "d3", "d4", "d5", "d6")}
    graph = build_workflow(agent_fns=agent_fns)
    state = await graph.ainvoke(
        {
            "task_id": str(uuid.uuid4()),
            "document_id": "",
            "document_text": text,
        }
    )
    return state.get("findings", [])


def run_workflow(text: str, model: str) -> list[dict]:
    return asyncio.run(_async_run_workflow(text, model))


def _norm_dim(dim: str | None) -> str:
    from app.agents.dimension_agent import normalize_dimension

    return normalize_dimension(dim, "d1")


def _finding_dim(finding: dict) -> str:
    dim = str(finding.get("dimension") or "")
    if dim == "crossConsistency":
        return dim
    return _norm_dim(dim)


def _match_finding(finding: dict, expected: dict) -> bool:
    """维度一致 + 违规性一致即命中（关键词/证据不强求，避免 LLM 措辞差异误判）。"""
    if _finding_dim(finding) != expected["dimension"]:
        return False
    verdict = str(finding.get("verdict") or "")
    # unclear 表示"待人工复核/降级"，既非违规也非合规，不应匹配任何金标项
    is_violation = verdict not in ("compliant", "ok", "notApplicable", "", "unclear")
    if expected.get("dimension") == "crossConsistency":
        expected_is_violation = True
    else:
        expected_is_violation = expected["verdict"] == "nonCompliant"
    return is_violation == expected_is_violation


# ── 单份评估 ─────────────────────────────────────────────────────
def evaluate_single(kind: str, text: str, ann: dict, model: str) -> dict:
    extracted_entities, extracted_relations = extract_graph(text)
    expected_entities = ann.get("entities") or []
    expected_relations = ann.get("relations") or []
    entity_f1_val = _f1(expected_entities, extracted_entities, _entity_hit)
    relation_f1_val = _f1(expected_relations, extracted_relations, _relation_hit)

    findings = run_workflow(text, model)
    findings = [f for f in findings if f.get("dimension")]

    expected_findings = ann.get("expectedFindings") or []
    matched = [False] * len(expected_findings)
    matched_finding = [None] * len(expected_findings)  # 命中金标项的具体 finding（取 clauseRef）
    for f in findings:
        for i, ex in enumerate(expected_findings):
            if not matched[i] and _match_finding(f, ex):
                matched[i] = True
                matched_finding[i] = f

    high_expect = [ex for ex in expected_findings if ex["level"] == "high"]
    high_hit = sum(1 for i, ex in enumerate(expected_findings) if ex["level"] == "high" and matched[i])
    high_recall = high_hit / len(high_expect) if high_expect else 1.0

    violations_found = [
        f for f in findings
        if f.get("verdict") not in ("compliant", "ok", "notApplicable", "", "unclear")
    ]
    true_pos = sum(matched)
    false_pos = max(0, len(violations_found) - true_pos)
    total_reported = len(violations_found)
    fpr = false_pos / total_reported if total_reported else 0.0

    clause_hits, clause_total = 0, 0
    for i, ex in enumerate(expected_findings):
        if not matched[i]:
            continue
        mf = matched_finding[i]
        if not mf:
            continue
        clause_total += 1
        ref = str(mf.get("clauseRef") or "")
        if ex.get("clauseRef") and (ref == ex["clauseRef"] or ex["clauseRef"] in ref):
            clause_hits += 1
    clause_acc = clause_hits / clause_total if clause_total else 1.0

    conflicts_expect = [ex for ex in expected_findings if ex["dimension"] == "crossConsistency"]
    conflict_hits = sum(
        1 for i, ex in enumerate(expected_findings) if ex["dimension"] == "crossConsistency" and matched[i]
    )
    conflict_recall = conflict_hits / len(conflicts_expect) if conflicts_expect else 1.0

    matched_refs = []
    for i, ex in enumerate(expected_findings):
        if not matched[i] or not matched_finding[i]:
            continue
        matched_refs.append({
            "dim": ex["dimension"],
            "expected": ex.get("clauseRef"),
            "actual": str(matched_finding[i].get("clauseRef") or ""),
            "verdict": str(matched_finding[i].get("verdict") or ""),
        })

    return {
        "id": ann["id"], "kind": kind,
        "entity_f1": entity_f1_val, "relation_f1": relation_f1_val,
        "high_risk_recall": high_recall, "false_positive_rate": fpr,
        "clause_accuracy": clause_acc, "conflict_detection": conflict_recall,
        "expected_count": len(expected_findings), "matched_count": sum(matched),
        "reported_violations": len(violations_found),
        "matched_refs": matched_refs,
        "missed": [expected_findings[i] for i in range(len(expected_findings)) if not matched[i]],
    }


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# ── 数据加载 ─────────────────────────────────────────────────────
def load_golden(limit: int | None) -> list[tuple[str, str, dict]]:
    items: list[tuple[str, str, dict]] = []
    single_dir = GOLDEN / "single"
    for json_path in sorted(single_dir.glob("*.json"))[: limit or 999]:
        ann = json.loads(json_path.read_text(encoding="utf-8"))
        text = (single_dir / ann["document"][0]).read_text(encoding="utf-8")
        items.append(("single", text, ann))

    if limit is None or len(items) < limit:
        multi_dir = GOLDEN / "multi"
        remaining = (limit or 999) - len(items)
        for json_path in sorted(multi_dir.glob("*.json"))[:remaining]:
            ann = json.loads(json_path.read_text(encoding="utf-8"))
            parts = [(multi_dir / name).read_text(encoding="utf-8") for name in ann["document"]]
            items.append(("multi", "\n\n--- 文档分隔 ---\n\n".join(parts), ann))
    return items


# ── 主流程 ─────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="M10 三层评估")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out", default=str(ROOT / "docs" / "eval_report.md"))
    args = parser.parse_args()

    items = load_golden(args.limit)
    est_calls = len(items) * 8
    print(f"载入金标 {len(items)} 份（limit={args.limit or 40}）")
    print(f"模型: {args.model} | 预估 LLM 调用 ≈ {est_calls} 次（6 维 + 反思 ≤2）", flush=True)

    results = [evaluate_single(kind, text, ann, args.model) for kind, text, ann in items]

    entity_f1 = avg([r["entity_f1"] for r in results])
    relation_f1 = avg([r["relation_f1"] for r in results])
    high_recall = avg([r["high_risk_recall"] for r in results])
    fpr = avg([r["false_positive_rate"] for r in results])
    clause_acc = avg([r["clause_accuracy"] for r in results])
    multi = [r for r in results if r["kind"] == "multi"]
    conflict = avg([r["conflict_detection"] for r in multi]) if multi else None

    # 单源指标（报告与 json 共用，禁改数）
    metrics = {
        "entity_f1": round(entity_f1, 4),
        "relation_f1": round(relation_f1, 4),
        "high_risk_recall": round(high_recall, 4),
        "false_positive_rate": round(fpr, 4),
        "clause_accuracy": round(clause_acc, 4),
        "conflict_detection": round(conflict, 4) if conflict is not None else None,
    }
    report = {
        "model": args.model, "count": len(results),
        "metrics": metrics, "thresholds": THRESHOLDS, "per_item": results,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _pass(val, thr, lower=False):
        if val is None:
            return "-"
        return "✅" if ((val <= thr) if lower else (val >= thr)) else "❌"

    lines = ["# 三层评估报告（M10）", "", f"- 评估时间：2026-08-24", f"- 模型：`{args.model}`", f"- 金标份数：{len(results)}", "", "## 指标总览", "", "| 指标 | 本次值 | 验收阈值 | 达标 |", "|---|---|---|---|"]
    lines.append(f"| 实体 F1 | {metrics['entity_f1']:.3f} | ≥{THRESHOLDS['entity_f1']:.2f} | {_pass(metrics['entity_f1'], THRESHOLDS['entity_f1'])} |")
    lines.append(f"| 关系 F1 | {metrics['relation_f1']:.3f} | ≥{THRESHOLDS['relation_f1']:.2f} | {_pass(metrics['relation_f1'], THRESHOLDS['relation_f1'])} |")
    lines.append(f"| 高风险召回 | {metrics['high_risk_recall']:.3f} | ≥{THRESHOLDS['high_risk_recall']:.2f} | {_pass(metrics['high_risk_recall'], THRESHOLDS['high_risk_recall'])} |")
    lines.append(f"| 误报率 | {metrics['false_positive_rate']:.3f} | ≤{THRESHOLDS['false_positive_rate']:.2f} | {_pass(metrics['false_positive_rate'], THRESHOLDS['false_positive_rate'], True)} |")
    lines.append(f"| 条款引用准确率 | {metrics['clause_accuracy']:.3f} | ≥{THRESHOLDS['clause_accuracy']:.2f} | {_pass(metrics['clause_accuracy'], THRESHOLDS['clause_accuracy'])} |")
    if metrics["conflict_detection"] is not None:
        lines.append(f"| 交叉矛盾检出率 | {metrics['conflict_detection']:.3f} | ≥{THRESHOLDS['conflict_detection']:.2f} | {_pass(metrics['conflict_detection'], THRESHOLDS['conflict_detection'])} |")
    else:
        lines.append(f"| 交叉矛盾检出率 | N/A（本次无多文档） | ≥{THRESHOLDS['conflict_detection']:.2f} | - |")
    lines.append("")
    lines.append("## 每份明细")
    lines.append("")
    for r in results:
        lines.append(f"### {r['id']}（{r['kind']}）")
        lines.append(f"- 实体F1 {r['entity_f1']:.2f} / 关系F1 {r['relation_f1']:.2f} / 高风险召回 {r['high_risk_recall']:.2f} / 误报率 {r['false_positive_rate']:.2f} / 条款 {r['clause_accuracy']:.2f} / 矛盾 {r['conflict_detection']:.2f}")
        lines.append(f"- 命中 {r['matched_count']}/{r['expected_count']}，系统报告违规 {r['reported_violations']} 项")
        if r["missed"]:
            lines.append("- **未命中**：" + "；".join(f"{m['dimension']}:{m.get('clauseRef') or '矛盾'}" for m in r["missed"]))
        lines.append("")
    lines.append("## 失败案例分析")
    lines.append("")
    for r in results:
        for m in r["missed"]:
            lines.append(f"- **{r['id']}** {m['dimension']} 未检出（期望引用 {m.get('clauseRef') or '矛盾'}，证据：{m.get('evidenceText')}）")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")

    # 中间结果 JSON（与报告同源）
    (ROOT / "docs" / "eval_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print(f"指标汇总（{len(results)} 份, model={args.model}）")
    print(f"  实体 F1:        {metrics['entity_f1']:.3f} (阈值 ≥{THRESHOLDS['entity_f1']})")
    print(f"  关系 F1:        {metrics['relation_f1']:.3f} (阈值 ≥{THRESHOLDS['relation_f1']})")
    print(f"  高风险召回:     {metrics['high_risk_recall']:.3f} (阈值 ≥{THRESHOLDS['high_risk_recall']})")
    print(f"  误报率:         {metrics['false_positive_rate']:.3f} (阈值 ≤{THRESHOLDS['false_positive_rate']})")
    print(f"  条款引用准确率: {metrics['clause_accuracy']:.3f} (阈值 ≥{THRESHOLDS['clause_accuracy']})")
    if metrics["conflict_detection"] is not None:
        print(f"  交叉矛盾检出率: {metrics['conflict_detection']:.3f} (阈值 ≥{THRESHOLDS['conflict_detection']})")
    else:
        print("  交叉矛盾检出率: N/A（本次无多文档）")
    print(f"\n报告已写入: {out_path}")
    print(f"结果 JSON 已写入: {ROOT / 'docs' / 'eval_results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
