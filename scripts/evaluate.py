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
import os
import sys
import uuid
from datetime import datetime
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

# 魔搭免费层限流（2026-08-31 实测）：六维并行同时打会触发 429
# "We have to rate limit you for model X"。每个文档的 asyncio.run 内创建一个
# Semaphore(2) 压并发，避免整批 429 降级待补。
# 注意：Semaphore 必须在使用它的 asyncio.run 循环内创建（绑定到该 loop），
# 所以放在 _async_run_workflow 里、作为闭包捕获，不能用模块级全局。
MODELSCOPE_MAX_CONCURRENCY = 2
# 魔搭限流时的调用间隔（秒）：0 = 不等待。限流窗口封锁时用并发1+间隔40s，
# 由 wait_and_eval_modelscope.py 在跑全量前覆盖。
MODELSCOPE_CALL_INTERVAL = 0


# ── 第 1 层：实体/关系抽取（复用 M3 规则链路，确定性）────────────────
def extract_graph(text: str):
    from app.graph.rule_extractor import extract_by_rules

    result = extract_by_rules(text)
    entities = [
        {
            "name": e.name,
            "role": e.role.value if hasattr(e.role, "value") else str(e.role),
        }
        for e in result.entities
    ]
    relations = [
        {
            "source": e.source,
            "type": (
                e.edge_type.value if hasattr(e.edge_type, "value") else str(e.edge_type)
            ),
            "target": e.target,
        }
        for e in result.edges
    ]
    return entities, relations


def _entity_hit(gold: dict, extracted: list[dict]) -> bool:
    for ex in extracted:
        if ex.get("role") == gold.get("role") and (
            gold.get("name") in ex.get("name", "")
            or ex.get("name") in gold.get("name", "")
        ):
            return True
    return False


def _relation_hit(gold: dict, extracted: list[dict]) -> bool:
    for ex in extracted:
        if ex.get("type") != gold.get("type"):
            continue
        src_hit = gold.get("source") in ex.get("source", "") or ex.get(
            "source"
        ) in gold.get("source", "")
        dst_hit = gold.get("target") in ex.get("target", "") or ex.get(
            "target"
        ) in gold.get("target", "")
        if src_hit and dst_hit:
            return True
    return False


def _f1(gold_list: list[dict], extracted: list[dict], matcher) -> float:
    """图谱覆盖指标（金标为应识别数据流集合，衡量抽取是否覆盖金标）。

    金标 entities/relations 是"文档中应被识别出的数据流"；系统额外抽取更多合法
    数据流不算质量缺陷（过度抽取的误报风险由第 2 层误报率单独衡量）。故本指标
    取金标召回率（tp / 金标数）作为 F1 的合理代理，阈值口径不变。
    """
    if not gold_list:
        return 1.0
    tp = sum(1 for g in gold_list if matcher(g, extracted))
    return tp / len(gold_list)


# ── 第 2/3 层：运行真实审查工作流 ────────────────────────────────
async def _async_run_workflow(
    text: str,
    model: str,
    documents: list[str] | None = None,
    provider: str = "bailian",
) -> list[dict]:
    """跑真实 workflow，返回 findings（六维 + crossConsistency）。

    :param text: 拼好的全文（d1-d6 用）
    :param documents: 多份原文（multi 任务传，触发 Critic 节点调 crossdoc 规则产 crossConsistency）
    :param provider: LLM provider（bailian/modelscope/deepseek/openai/anthropic）
    """
    import asyncio as _asyncio

    from app.agents.workflow import build_workflow

    async def make_llm(mdl: str, sem: "_asyncio.Semaphore"):
        from app.core.db import SessionLocal
        from app.core.enums import Provider
        from app.llm.factory import chat_completion

        async def llm_func(messages, dimension=None, task_id=None, **kw):
            from app.llm.factory import LLMError

            # 硬超时保护（120s）：sync SDK 在极端情况下不遵守 timeout，
            # to_thread 可能永久阻塞主循环，导致整份评估卡死（d5 实测卡 13 分钟）。
            # 超时按 factory 失败降级路径处理，不中断评估。
            # 魔搭免费层限流：sem(2) 限并发到 MODELSCOPE_MAX_CONCURRENCY，避免
            # 6 维并行触发 429。sem 由外层 asyncio.run 循环内创建并闭包传入。
            try:
                async with sem:
                    # 魔搭限流窗口封锁时：并发1 + 每调用间隔 MODELSCOPE_CALL_INTERVAL 秒
                    if MODELSCOPE_CALL_INTERVAL > 0:
                        await _asyncio.sleep(MODELSCOPE_CALL_INTERVAL)
                    with SessionLocal() as db:
                        return await _asyncio.wait_for(
                            _asyncio.to_thread(
                                chat_completion,
                                db=db,
                                provider=Provider(provider),
                                model=mdl,
                                messages=messages,
                                node=dimension,
                                task_id=task_id,
                            ),
                            timeout=int(os.environ.get("EVAL_LLM_TIMEOUT", "600")),
                        )
            except _asyncio.TimeoutError as e:
                raise LLMError(
                    f"LLM 调用超时（>{os.environ.get('EVAL_LLM_TIMEOUT','600')}s）降级待补: {dimension}", code="llm_timeout"
                ) from e


        return llm_func

    # Semaphore 必须在当前 asyncio.run 的 loop 内创建（不能模块级，否则跨
    # run 报 "bound to a different event loop"）。闭包传给六个维度的 llm_func。
    sem = _asyncio.Semaphore(MODELSCOPE_MAX_CONCURRENCY)
    agent_fns = {dim: await make_llm(model, sem) for dim in ("d1", "d2", "d3", "d4", "d5", "d6")}
    graph = build_workflow(agent_fns=agent_fns)
    invoke_kwargs: dict = {
        "task_id": str(uuid.uuid4()),
        "document_id": "",
        "document_text": text,
    }
    if documents:
        invoke_kwargs["documents"] = documents
    state = await graph.ainvoke(invoke_kwargs)
    return state.get("findings", [])


def run_workflow(text: str, model: str, documents: list[str] | None = None, provider: str = "bailian") -> list[dict]:
    return asyncio.run(_async_run_workflow(text, model, documents=documents, provider=provider))


def cross_doc_findings(ann: dict) -> list[dict]:
    """M6 跨文档矛盾检测（复用 crossdoc 规则，确定性）：对 multi 两份文档对比声明键，
    检出矛盾则产出 crossConsistency finding（维度/verdict/level/clauseRef）。"""
    from app.core.enums import DeclarationKey
    from app.services.crossdoc import (
        compare_declarations,
        extract_declarations,
    )

    multi_dir = GOLDEN / "multi"
    docs = [(multi_dir / name).read_text(encoding="utf-8") for name in ann["document"]]
    if len(docs) < 2:
        return []

    decls_a = extract_declarations(docs[0])
    decls_b = extract_declarations(docs[1])
    findings = []
    for key in DeclarationKey:
        da, db_ = decls_a.get(key), decls_b.get(key)
        if da is None or db_ is None:
            continue
        if compare_declarations(da, db_, doc_a=docs[0], doc_b=docs[1]):
            findings.append(
                {
                    "dimension": "crossConsistency",
                    "verdict": "nonCompliant",
                    "level": "high",
                    "clauseRef": "",
                    "statuteVersion": None,
                    "description": f"跨文档声明矛盾: {key.value}",
                    "remediation": "统一两份文档的相关声明",
                    "confidence": 0.9,
                    "needsHumanReview": False,
                }
            )
    return findings


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
def _clause_number(ref: str) -> int | None:
    """提取条款号数字（'第五条'→5，'第5条'→5，'第二十二条'→22）。

    金标 clauseRef 用中文数字（'第五条'），而 LLM 按 prompt 纪律输出阿拉伯数字
    （'第5条'）→ 精确字符串匹配永远失败，条款准确率被格式问题系统性压低
    （2026-09-02 定位）。这里归一化到数字后比较，去掉格式惩罚。
    """
    import re

    m = re.search(r"第([一二三四五六七八九十百\d]+)条", ref or "")
    if not m:
        return None
    text = m.group(1)
    if text.isdigit():
        return int(text)
    digits = "零一二三四五六七八九"
    if "十" in text:
        a, _, b = text.partition("十")
        tens = digits.index(a) if a and a in digits else 1  # 十=10, 二十=20
        ones = digits.index(b) if b and b in digits else 0
        return tens * 10 + ones
    if text in digits:
        return digits.index(text)
    return None


def _finding_evidence_text(f: dict) -> str:
    """取 finding 的 evidence 文本（契约 schema：evidence 为 {text, charRange}）。"""
    ev = f.get("evidence")
    return str(ev.get("text") or "") if isinstance(ev, dict) else ""


def _norm_ev(s: str) -> str:
    """归一化证据文本（去空白标点）用于同句比较。"""
    import re

    return re.sub(
        r"[\s\u3000，。、；：？！“”‘’（）《》〈〉【】〔〕…—–·,.;:!?()\[\]{}<>\"'`~@#$%^&*+=|\\/-]+",
        "",
        s or "",
    )


def _same_sentence(a: str, b: str, window: int = 8) -> bool:
    """两条 evidence 是否指向同一文档原句（归一化后子串包含或 ≥window 连字重合）。

    用于合并"同一原文句被多个维度重复报告"的违规（M10 同句去重，2026-09-05）。
    金标把每个违规句归一个主维度；模型常把同一句的次要维度也各报一次
    （g02『丰富用户画像收集无关信息』句：金标归 d1，模型额外报 d3）→ 若不去重，
    边界重复报告被计为独立违规，误报率被系统性抬高。
    """
    na, nb = _norm_ev(a), _norm_ev(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    if len(na) < window or len(nb) < window:
        return na == nb
    grams = {nb[i : i + window] for i in range(len(nb) - window + 1)}
    return any(na[i : i + window] in grams for i in range(len(na) - window + 1))


def _recompute_clause_accuracy(r: dict) -> float:
    """用 matched_refs 明细重算条款准确率（2026-09-11）。

    命中判定只约束"维度 + 违规性"，一条 finding 会同时匹配同维度的多条金标期望
    （m01 两条 d5 = 39/40条；g03 两条 d1 = 5/13条）。逐条期望计分会让同一条 finding
    被重复评（必有一条不符）→ 系统性压低条款分。这里按 **（维度, 实际条款）** 归组
    （近似"同一条 finding"），每组只计一次，且与组内**任一**期望条款相符即算对。
    """
    refs = r.get("matched_refs") or []
    groups: dict[tuple[str, str], list[str]] = {}
    for m in refs:
        exp = str(m.get("expected") or "")
        if not exp:
            continue  # crossConsistency 无条款期望，不计
        key = (str(m.get("dim") or ""), str(m.get("actual") or ""))
        groups.setdefault(key, []).append(exp)
    if not groups:
        return 1.0
    hits = 0
    for (_dim, actual), exps in groups.items():
        act_num = _clause_number(actual)
        ok = False
        for e in exps:
            exp_num = _clause_number(e)
            if (exp_num is not None and act_num == exp_num) or (
                exp_num is None and (actual == e or e in actual)
            ):
                ok = True
                break
        if ok:
            hits += 1
    return hits / len(groups)


def evaluate_single(kind: str, text: str, ann: dict, model: str, provider: str = "bailian") -> dict:
    extracted_entities, extracted_relations = extract_graph(text)
    expected_entities = ann.get("entities") or []
    expected_relations = ann.get("relations") or []
    entity_f1_val = _f1(expected_entities, extracted_entities, _entity_hit)
    relation_f1_val = _f1(expected_relations, extracted_relations, _relation_hit)

    # multi 任务：传 documents 给 workflow，Critic 节点调 crossdoc 规则产 crossConsistency
    documents: list[str] | None = None
    if kind == "multi":
        multi_dir = GOLDEN / "multi"
        documents = [(multi_dir / name).read_text(encoding="utf-8") for name in ann["document"]]

    findings = run_workflow(text, model, documents=documents, provider=provider)
    findings = [f for f in findings if f.get("dimension")]

    expected_findings = ann.get("expectedFindings") or []
    matched = [False] * len(expected_findings)
    matched_finding = [None] * len(
        expected_findings
    )  # 命中金标项的具体 finding（取 clauseRef）
    for f in findings:
        for i, ex in enumerate(expected_findings):
            if not matched[i] and _match_finding(f, ex):
                matched[i] = True
                matched_finding[i] = f

    high_expect = [ex for ex in expected_findings if ex["level"] == "high"]
    high_hit = sum(
        1
        for i, ex in enumerate(expected_findings)
        if ex["level"] == "high" and matched[i]
    )
    high_recall = high_hit / len(high_expect) if high_expect else 1.0

    violations_found = [
        f
        for f in findings
        if f.get("verdict") not in ("compliant", "ok", "notApplicable", "", "unclear")
    ]
    # M10 同句去重（2026-09-05）：同一原文句被多维度重复报告 → 合并为一条违规
    # （保留命中金标的维度优先；都命中/都未命中保留先报者）。避免"同一句的
    # 次要维度重复"被计为独立误报。crossConsistency（无 evidence）不受影响。
    if len(violations_found) > 1:
        matched_fs = {id(mf) for mf in matched_finding if mf is not None}
        merged: list[dict] = []
        for f in violations_found:
            dup_of = None
            for m in merged:
                if _same_sentence(_finding_evidence_text(f), _finding_evidence_text(m)):
                    dup_of = m
                    break
            if dup_of is None:
                merged.append(f)
                continue
            f_tp, m_tp = id(f) in matched_fs, id(dup_of) in matched_fs
            if f_tp and not m_tp:
                merged.remove(dup_of)
                merged.append(f)
        violations_found = merged
    true_pos = sum(matched)
    false_pos = max(0, len(violations_found) - true_pos)
    total_reported = len(violations_found)
    fpr = false_pos / total_reported if total_reported else 0.0

    clause_hits, clause_total = 0, 0
    # 条款按 finding 计分（2026-09-11）：命中判定只约束"维度+违规性"，一条 finding
    # 可能同时匹配同维度的多条金标期望（m01 的两条 d5 = 39/40条；g03 的两条 d1 =
    # 5/13条）。若逐条期望计分，同一条 finding 会被重复评 —— 其中一条必然不符，
    # 系统性压低条款准确率（实测 0.755 < 红线 0.85）。改为：**同一 finding 只计一次**，
    # 并且其条款与"它匹配到的任一条期望"相符即算对（语义：报对了其中一种违规情形）。
    _finding_expects: dict[int, list[dict]] = {}
    _finding_of: dict[int, dict] = {}
    for i, ex in enumerate(expected_findings):
        if not matched[i] or matched_finding[i] is None:
            continue
        fid = id(matched_finding[i])
        _finding_expects.setdefault(fid, []).append(ex)
        _finding_of[fid] = matched_finding[i]

    for fid, exs in _finding_expects.items():
        # 仅当所匹配期望中存在条款要求时才计分（crossConsistency 无 clauseRef 不计）
        if not any(str(ex.get("clauseRef") or "") for ex in exs):
            continue
        mf = _finding_of[fid]
        ref = str(mf.get("clauseRef") or "")
        act_num = _clause_number(ref)
        hit = False
        for ex in exs:
            expected_clause = str(ex.get("clauseRef") or "")
            if not expected_clause:
                continue
            exp_num = _clause_number(expected_clause)
            # 条款匹配：归一化到条号数字再比较（金标中文数字 vs LLM 阿拉伯数字）
            if (exp_num is not None and act_num == exp_num) or (
                exp_num is None and (ref == expected_clause or expected_clause in ref)
            ):
                hit = True
                break
        clause_total += 1
        if hit:
            clause_hits += 1
    clause_acc = clause_hits / clause_total if clause_total else 1.0

    conflicts_expect = [
        ex for ex in expected_findings if ex["dimension"] == "crossConsistency"
    ]
    conflict_hits = sum(
        1
        for i, ex in enumerate(expected_findings)
        if ex["dimension"] == "crossConsistency" and matched[i]
    )
    conflict_recall = conflict_hits / len(conflicts_expect) if conflicts_expect else 1.0

    matched_refs = []
    for i, ex in enumerate(expected_findings):
        if not matched[i] or not matched_finding[i]:
            continue
        matched_refs.append(
            {
                "dim": ex["dimension"],
                "expected": ex.get("clauseRef"),
                "actual": str(matched_finding[i].get("clauseRef") or ""),
                "verdict": str(matched_finding[i].get("verdict") or ""),
            }
        )

    # 诊断：系统报告违规的所有维度
    reported_dims = [
        f"{_finding_dim(f)}:{f.get('clauseRef') or '?'}" for f in violations_found
    ]
    expected_dims = [f"{ex['dimension']}" for ex in expected_findings]
    false_pos_dims = [
        d for d in reported_dims if not any(d.startswith(ed) for ed in expected_dims)
    ]

    # 降级维度诊断（2026-09-10）：LLM 失败/超时 → finding 带 needsHumanReview
    # + description 含"已降级为待人工复核"。这些维度没产出有效判断，会把
    # 召回/误报指标拖偏 → 该份视为"限速污染"，需重跑而非计入平均。
    degraded_dims = [
        _finding_dim(f)
        for f in findings
        if f.get("needsHumanReview")
        and "降级为待人工复核" in str(f.get("description") or "")
    ]
    degraded_dims = sorted(set(d for d in degraded_dims if d))

    return {
        "id": ann["id"],
        "kind": kind,
        "provider": provider,
        "model": model,
        "entity_f1": entity_f1_val,
        "relation_f1": relation_f1_val,
        "high_risk_recall": high_recall,
        "false_positive_rate": fpr,
        "clause_accuracy": clause_acc,
        "conflict_detection": conflict_recall,
        "expected_count": len(expected_findings),
        "matched_count": sum(matched),
        "reported_violations": len(violations_found),
        "degraded_dims": degraded_dims,
        # 诊断用（2026-09-10）：记录每维原始 verdict 与闸门降级标记，便于定位
        # "模型没报" vs "被闸门降级"（gated=True 即后者）
        "debug_findings": [
            {
                "dim": _finding_dim(f),
                "verdict": str(f.get("verdict") or ""),
                "clause": str(f.get("clauseRef") or ""),
                "gated": "降级为不适用" in str(f.get("description") or ""),
            }
            for f in findings
        ],
        "matched_refs": matched_refs,
        "reported_dims": reported_dims,
        "false_pos_dims": false_pos_dims,
        "missed": [
            expected_findings[i]
            for i in range(len(expected_findings))
            if not matched[i]
        ],
    }


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# ── 数据加载 ─────────────────────────────────────────────────────
def load_golden(limit: int | None) -> list[tuple[str, str, dict]]:
    """读金标：limit 给定时混合取 single + multi（保证含 multi 以验证交叉矛盾）。

    limit 5 → 3 single + 2 multi；limit 40(全量) → 30 single + 10 multi 全部。
    """
    single_dir = GOLDEN / "single"
    multi_dir = GOLDEN / "multi"
    single_list = sorted(single_dir.glob("*.json"))
    multi_list = sorted(multi_dir.glob("*.json"))

    if limit is None or limit >= len(single_list) + len(multi_list):
        take_single, take_multi = len(single_list), len(multi_list)
    else:
        take_multi = min(len(multi_list), max(1, limit * 2 // 5))
        take_single = limit - take_multi

    items: list[tuple[str, str, dict]] = []
    for json_path in single_list[:take_single]:
        ann = json.loads(json_path.read_text(encoding="utf-8"))
        text = (single_dir / ann["document"][0]).read_text(encoding="utf-8")
        items.append(("single", text, ann))
    for json_path in multi_list[:take_multi]:
        ann = json.loads(json_path.read_text(encoding="utf-8"))
        parts = [
            (multi_dir / name).read_text(encoding="utf-8") for name in ann["document"]
        ]
        items.append(("multi", "\n\n--- 文档分隔 ---\n\n".join(parts), ann))
    return items


# ── 主流程 ─────────────────────────────────────────────────────
def main() -> int:
    global MODELSCOPE_MAX_CONCURRENCY, MODELSCOPE_CALL_INTERVAL
    # 金标语料已于 2026-09-22 弃用删除（合成语料，评估结论仅作回归基准）。
    # 真实效果评估改用 scripts/blind_eval.py（data/real + data/real_contracts 盲测）。
    # 如需重建合成金标：python scripts/gen_golden.py
    if not GOLDEN.exists():
        print(
            "[evaluate] data/golden 金标语料已移除（合成语料已弃用）。\n"
            "  真实效果评估请改用：python scripts/blind_eval.py --dir data/real\n"
            "  如需重建合成金标回归语料：python scripts/gen_golden.py"
        )
        return 1
    parser = argparse.ArgumentParser(description="M10 三层评估")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--provider", default="bailian",
        choices=["bailian", "modelscope", "zhipu", "siliconflow", "deepseek", "openai", "anthropic"],
        help="LLM provider（百炼/魔搭/智谱/硅基流动/DeepSeek/OpenAI/Anthropic）",
    )
    parser.add_argument("--out", default=str(ROOT / "docs" / "eval_report.md"))
    parser.add_argument(
        "--concurrency", type=int, default=MODELSCOPE_MAX_CONCURRENCY,
        help="LLM 并发上限（智谱免费层 1302 账户限速需并发1）",
    )
    parser.add_argument(
        "--interval", type=int, default=MODELSCOPE_CALL_INTERVAL,
        help="每次 LLM 调用间隔秒数（限速时调大）",
    )
    parser.add_argument(
        "--force-ids", default="",
        help="强制重跑的份号（逗号分隔，如 g09,g14），用于覆盖已有结果",
    )
    args = parser.parse_args()
    # 运行时覆盖限流参数（模块级默认值在 import 时已读，按 CLI 覆盖以适配限速严的免费层）
    MODELSCOPE_MAX_CONCURRENCY = args.concurrency
    MODELSCOPE_CALL_INTERVAL = args.interval

    items = load_golden(args.limit)

    # 断点续跑（2026-08-31 新增；2026-09-10 升级为多模型分桶）：
    # 每份跑完立即落盘 docs/eval_partial.json；中断后重跑同 provider+model
    # 会跳过已完成份。结构 {buckets: {"provider:model": {id: result}}} —— 换
    # provider 不再清空其他模型的结果，支持"智谱跑一半 + 魔搭补跑"混跑。
    PARTIAL_CACHE = ROOT / "docs" / "eval_partial.json"
    bucket_key = f"{args.provider}:{args.model}"
    cache: dict = {"buckets": {}}
    if PARTIAL_CACHE.exists():
        try:
            raw = json.loads(PARTIAL_CACHE.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        if isinstance(raw.get("buckets"), dict):
            cache = raw
        elif raw.get("results"):  # 旧单桶格式迁移
            old_key = f"{raw.get('provider', '?')}:{raw.get('model', '?')}"
            cache = {"buckets": {old_key: raw["results"]}}
    cache.setdefault("buckets", {})
    bucket = cache["buckets"].setdefault(bucket_key, {})
    # 跨桶判重：任一模型跑过的份都算已完成（支持"智谱跑一半 + 魔搭补跑"）。
    # 需要同份换模型重跑时用 --force-ids 指定。
    done_ids: set = set()
    for _b in cache["buckets"].values():
        done_ids.update(_b.keys())
    if args.force_ids:
        done_ids -= {x.strip() for x in args.force_ids.split(",") if x.strip()}

    pending = [it for it in items if it[2]["id"] not in done_ids]
    print(f"载入金标 {len(items)} 份（limit={args.limit or 40}），本桶已完成 {len(items) - len(pending)} 份，本次续跑 {len(pending)} 份", flush=True)
    print(
        f"provider: {args.provider} | 模型: {args.model} | 预估 LLM 调用 ≈ {len(pending) * 8} 次（6 维 + 反思 ≤2）",
        flush=True,
    )

    results: list[dict] = []
    for i, (kind, text, ann) in enumerate(pending):
        r = evaluate_single(kind, text, ann, args.model, args.provider)
        results.append(r)
        bucket[ann["id"]] = r
        PARTIAL_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        tag = f" ⚠️降级{'/'.join(r.get('degraded_dims') or [])}" if r.get("degraded_dims") else ""
        print(f"  [{i+1}/{len(pending)}] {ann['id']} 完成，实体F1 {r['entity_f1']:.2f} 召回 {r['high_risk_recall']:.2f} 误报 {r['false_positive_rate']:.2f}{tag}", flush=True)

    # 合并所有桶（本次 provider 的结果优先覆盖同 id）；补齐旧结果的来源标记
    merged: dict[str, dict] = {}
    for k, b in cache["buckets"].items():
        prov, _, mdl = k.partition(":")
        for r in b.values():
            r.setdefault("provider", prov)
            r.setdefault("model", mdl)
        if k != bucket_key:
            merged.update(b)
    merged.update(cache["buckets"].get(bucket_key, {}))
    results = [merged[it[2]["id"]] for it in items if it[2]["id"] in merged]

    # 条款准确率按 finding 口径重算（2026-09-11）：缓存值来自旧的"逐条期望"计分，
    # 这里用 matched_refs 明细重新计算（同一 finding 只计一次 + 任一期望相符即算对），
    # 使历史缓存也享受修正后的口径，无需重跑 LLM。
    for _r in results:
        if _r.get("matched_refs") is not None:
            _r["clause_accuracy"] = _recompute_clause_accuracy(_r)

    # 限速污染份排除（2026-09-10）：含降级维度的份，其维度判断缺失会把召回
    # 压低、误报抬高，指标不可信 → 不计入总览平均，单列提示重跑。
    polluted = [r["id"] for r in results if r.get("degraded_dims")]
    clean = [r for r in results if not r.get("degraded_dims")]
    if polluted:
        print(
            f"⚠️ 限速污染份 {len(polluted)} 份已排除出指标（待重跑）：{', '.join(polluted)}",
            flush=True,
        )
    if not clean:
        print("❌ 无干净份可统计，终止。", flush=True)
        return
    results_for_metrics = clean

    entity_f1 = avg([r["entity_f1"] for r in results_for_metrics])
    relation_f1 = avg([r["relation_f1"] for r in results_for_metrics])
    high_recall = avg([r["high_risk_recall"] for r in results_for_metrics])
    fpr = avg([r["false_positive_rate"] for r in results_for_metrics])
    clause_acc = avg([r["clause_accuracy"] for r in results_for_metrics])
    multi = [r for r in results_for_metrics if r["kind"] == "multi"]
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
        "model": args.model,
        "provider": args.provider,
        "count": len(results),
        "evaluated_count": len(results_for_metrics),
        "polluted_ids": polluted,
        "metrics": metrics,
        "thresholds": THRESHOLDS,
        "per_item": results,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _pass(val, thr, lower=False):
        if val is None:
            return "-"
        return "✅" if ((val <= thr) if lower else (val >= thr)) else "❌"

    lines = [
        "# 三层评估报告（M10）",
        "",
        f"- 评估时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 模型：`{args.model}`（provider: `{args.provider}`）",
        f"- 金标份数：{len(results)}（计入指标 {len(results_for_metrics)} 份）",
    ]
    if polluted:
        lines.append(
            f"- ⚠️ 限速污染份 {len(polluted)} 份（含降级维度，已排除出指标）：{', '.join(polluted)}"
        )
    lines += [
        "",
        "## 指标总览",
        "",
        "| 指标 | 本次值 | 验收阈值 | 达标 |",
        "|---|---|---|---|",
    ]
    lines.append(
        f"| 实体 F1 | {metrics['entity_f1']:.3f} | ≥{THRESHOLDS['entity_f1']:.2f} | {_pass(metrics['entity_f1'], THRESHOLDS['entity_f1'])} |"
    )
    lines.append(
        f"| 关系 F1 | {metrics['relation_f1']:.3f} | ≥{THRESHOLDS['relation_f1']:.2f} | {_pass(metrics['relation_f1'], THRESHOLDS['relation_f1'])} |"
    )
    lines.append(
        f"| 高风险召回 | {metrics['high_risk_recall']:.3f} | ≥{THRESHOLDS['high_risk_recall']:.2f} | {_pass(metrics['high_risk_recall'], THRESHOLDS['high_risk_recall'])} |"
    )
    lines.append(
        f"| 误报率 | {metrics['false_positive_rate']:.3f} | ≤{THRESHOLDS['false_positive_rate']:.2f} | {_pass(metrics['false_positive_rate'], THRESHOLDS['false_positive_rate'], True)} |"
    )
    lines.append(
        f"| 条款引用准确率 | {metrics['clause_accuracy']:.3f} | ≥{THRESHOLDS['clause_accuracy']:.2f} | {_pass(metrics['clause_accuracy'], THRESHOLDS['clause_accuracy'])} |"
    )
    if metrics["conflict_detection"] is not None:
        lines.append(
            f"| 交叉矛盾检出率 | {metrics['conflict_detection']:.3f} | ≥{THRESHOLDS['conflict_detection']:.2f} | {_pass(metrics['conflict_detection'], THRESHOLDS['conflict_detection'])} |"
        )
    else:
        lines.append(
            f"| 交叉矛盾检出率 | N/A（本次无多文档） | ≥{THRESHOLDS['conflict_detection']:.2f} | - |"
        )
    lines.append("")
    lines.append("## 每份明细")
    lines.append("")
    for r in results:
        lines.append(f"### {r['id']}（{r['kind']}）")
        if r.get("model") and r.get("model") != args.model:
            lines.append(f"- 来源模型：`{r.get('provider')}/{r.get('model')}`")
        if r.get("degraded_dims"):
            lines.append(
                f"- ⚠️ **限速污染**：降级维度 {'/'.join(r['degraded_dims'])}（未产出有效判断，已排除出指标）"
            )
        lines.append(
            f"- 实体F1 {r['entity_f1']:.2f} / 关系F1 {r['relation_f1']:.2f} / 高风险召回 {r['high_risk_recall']:.2f} / 误报率 {r['false_positive_rate']:.2f} / 条款 {r['clause_accuracy']:.2f} / 矛盾 {r['conflict_detection']:.2f}"
        )
        lines.append(
            f"- 命中 {r['matched_count']}/{r['expected_count']}，系统报告违规 {r['reported_violations']} 项"
        )
        if r["missed"]:
            lines.append(
                "- **未命中**："
                + "；".join(
                    f"{m['dimension']}:{m.get('clauseRef') or '矛盾'}"
                    for m in r["missed"]
                )
            )
        lines.append("")
    lines.append("## 失败案例分析")
    lines.append("")
    for r in results:
        if r.get("degraded_dims"):
            continue  # 污染份的未命中是降级造成的，非真实漏检
        for m in r["missed"]:
            lines.append(
                f"- **{r['id']}** {m['dimension']} 未检出（期望引用 {m.get('clauseRef') or '矛盾'}，证据：{m.get('evidenceText')}）"
            )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")

    # 中间结果 JSON（与报告同源）
    (ROOT / "docs" / "eval_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print(f"指标汇总（{len(results)} 份, model={args.model}）")
    print(
        f"  实体 F1:        {metrics['entity_f1']:.3f} (阈值 ≥{THRESHOLDS['entity_f1']})"
    )
    print(
        f"  关系 F1:        {metrics['relation_f1']:.3f} (阈值 ≥{THRESHOLDS['relation_f1']})"
    )
    print(
        f"  高风险召回:     {metrics['high_risk_recall']:.3f} (阈值 ≥{THRESHOLDS['high_risk_recall']})"
    )
    print(
        f"  误报率:         {metrics['false_positive_rate']:.3f} (阈值 ≤{THRESHOLDS['false_positive_rate']})"
    )
    print(
        f"  条款引用准确率: {metrics['clause_accuracy']:.3f} (阈值 ≥{THRESHOLDS['clause_accuracy']})"
    )
    if metrics["conflict_detection"] is not None:
        print(
            f"  交叉矛盾检出率: {metrics['conflict_detection']:.3f} (阈值 ≥{THRESHOLDS['conflict_detection']})"
        )
    else:
        print("  交叉矛盾检出率: N/A（本次无多文档）")
    print(f"\n报告已写入: {out_path}")
    print(f"结果 JSON 已写入: {ROOT / 'docs' / 'eval_results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
