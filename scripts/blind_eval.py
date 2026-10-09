"""盲测脚本（M10 真实文本验证配套）：对真实隐私政策跑六维审查工作流，输出判定清单。

用法（backend/.venv 环境）：
  cd backend && .venv/Scripts/python.exe ../scripts/blind_eval.py --dir ../data/real --provider zhipu --model glm-4.5-flash

参数：
  --dir        真实文本目录（每份一个 .txt/.md，默认 data/real）
  --provider   bailian/modelscope/zhipu/deepseek/openai/anthropic（默认 zhipu）
  --model      LLM 模型名（默认 glm-4.5-flash）
  --concurrency  并发上限（免费层限流时用 1）
  --interval     每次调用间隔秒（限流窗口用 10）
  --max-chars    每份文档截取字符数（真实政策很长，默认 8000）
  --out          报告输出前缀（默认 docs/blind_eval）

行为：
  - 复用生产工作流 build_workflow（六维并行 + Critic + 反思 ≤2 轮），与线上链路一致；
  - 含证据锚定闸门与高危规则兜底（production 行为，不另作开关）；
  - 每条 finding 标注来源：description 含【确定性规则兜底】= 规则触发，否则为 LLM 判定；
  - 输出：{out}_results.json（机器可读）+ {out}_report.md（人工复核表，复核列留空）。

前置条件（与 evaluate.py 相同）：
  - 本地 Postgres(pgvector) 已启动且法条已入库（scripts/ingest_laws.py）；
  - 模型 key 可用（用户级 env：ZHIPU_API_KEY / Modelscope_API_KEY / OPENAI_API_KEY）。
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
_BACKEND = ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


async def _async_run_workflow(
    text: str, model: str, provider: str, concurrency: int, interval: int, timeout: int
) -> list[dict]:
    """跑完整生产工作流，返回 findings（六维 + crossConsistency）。"""
    import asyncio as _asyncio

    from app.agents.workflow import build_workflow
    from app.core.db import SessionLocal
    from app.core.enums import Provider
    from app.llm.factory import LLMError, chat_completion

    async def make_llm(mdl: str, sem: "_asyncio.Semaphore"):
        async def llm_func(messages, dimension=None, task_id=None, **kw):
            try:
                async with sem:
                    if interval > 0:
                        await _asyncio.sleep(interval)
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
                            timeout=timeout,
                        )
            except _asyncio.TimeoutError as e:
                raise LLMError(f"LLM 调用超时降级: {dimension}", code="llm_timeout") from e

        return llm_func

    sem = _asyncio.Semaphore(concurrency)
    agent_fns = {dim: await make_llm(model, sem) for dim in ("d1", "d2", "d3", "d4", "d5", "d6")}
    graph = build_workflow(agent_fns=agent_fns)
    state = await graph.ainvoke(
        {
            "task_id": str(uuid.uuid4()),
            "document_id": "",
            "document_text": text,
        }
    )
    return state.get("findings", [])


def run_workflow(text: str, model: str, provider: str, concurrency: int, interval: int, timeout: int) -> list[dict]:
    return asyncio.run(
        _async_run_workflow(text, model, provider, concurrency, interval, timeout)
    )


def is_rule_backed(f: dict) -> bool:
    """规则兜底判定：description 含【确定性规则兜底】标记（production 已注入）。"""
    return "确定性规则兜底" in str(f.get("description") or "")


def truncate(text: str, max_chars: int) -> tuple[str, bool]:
    """截断超长文本（真实政策可达数万字），返回 (截断后文本, 是否被截断)。"""
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def _write_report(args: argparse.Namespace, results: list[dict]) -> Path:
    """生成 Markdown 盲测报告（含人工复核留白列）。"""
    lines = [
        "# 真实隐私政策盲测报告",
        "",
        f"- 运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 模型：`{args.model}`（provider: `{args.provider}`）",
        f"- 文档数：{len(results)} | 截断阈值：{args.max_chars} 字符",
        "",
        "> 本报告为盲测原始输出，**未经人工复核**。复核后请在每行补结论（属实/误报/存疑）。",
        "",
    ]
    for r in results:
        lines += [
            f"## {r['file']}",
            f"- 原始长度 {r['raw_chars']} 字{'，已截断（注意：截断段之后的违规无法检出）' if r['truncated'] else ''}",
            "",
            "| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |",
            "|---|---|---|---|---|---|---|",
        ]
        fs = r["findings"]
        if not fs:
            lines.append("| （无判定输出） | | | | | | |")
        for f in fs:
            lines.append(
                "| {} | {} | {} | {} | {} | {} | |".format(
                    f.get("dimension") or "-",
                    f.get("verdict") or "-",
                    f.get("level") or "-",
                    f.get("clauseRef") or "-",
                    "是" if f.get("rule_backed") else "否",
                    (f.get("evidence") or f.get("description") or "-")[:80],
                )
            )
        lines.append("")
    out_md = Path(args.out + "_report.md")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_md


def main() -> int:
    parser = argparse.ArgumentParser(description="LegalEye 真实隐私政策盲测")
    parser.add_argument("--dir", default=str(ROOT / "data" / "real"))
    parser.add_argument("--provider", default="zhipu", choices=["bailian", "modelscope", "zhipu", "deepseek", "openai", "anthropic"])
    parser.add_argument("--model", default="glm-4.5-flash")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--max-chars", type=int, default=8000)
    parser.add_argument("--timeout", type=int, default=600, help="单次 LLM 调用超时秒数")
    parser.add_argument("--out", default=str(ROOT / "docs" / "blind_eval"))
    parser.add_argument(
        "--resume", action="store_true",
        help="断点续跑：加载已有 results.json，跳过已完成文档（每次跑完立即落盘，中断不丢进度）",
    )
    args = parser.parse_args()

    data_dir = Path(args.dir)
    if not data_dir.exists():
        print(f"❌ 目录不存在: {data_dir}（请先按 docs/blind_test_plan.md §2/§3 准备文本）")
        return 1
    files = sorted(p for p in data_dir.iterdir() if p.suffix.lower() in (".txt", ".md"))
    if not files:
        print(f"❌ {data_dir} 下没有 .txt/.md 文件")
        return 1
    print(f"发现 {len(files)} 份文档，provider={args.provider} model={args.model} concurrency={args.concurrency}")

    # ── 断点续跑：加载已有结果，跳过已完成文档 ──
    out_json = Path(args.out + "_results.json")
    done: dict[str, dict] = {}
    if args.resume and out_json.exists():
        try:
            prev = json.loads(out_json.read_text(encoding="utf-8"))
            done = {it["file"]: it for it in prev.get("items", [])}
            print(f"断点续跑：已加载 {len(done)} 份已完成结果，将跳过这些文档", flush=True)
        except (json.JSONDecodeError, KeyError):
            print("⚠️ 已有 results.json 无法解析，忽略并全新开始", flush=True)

    results: list[dict] = []
    for i, fp in enumerate(files, 1):
        if fp.name in done:
            print(f"  [{i}/{len(files)}] {fp.name}（已完成，跳过）", flush=True)
            results.append(done[fp.name])
            continue
        text = fp.read_text(encoding="utf-8", errors="ignore")
        raw_len = len(text)
        text, truncated = truncate(text, args.max_chars)
        print(f"  [{i}/{len(files)}] {fp.name}（原始 {raw_len} 字{'，已截断至 ' + str(args.max_chars) + ' 字' if truncated else ''}）…", flush=True)
        try:
            findings = run_workflow(
                text, args.model, args.provider, args.concurrency, args.interval, args.timeout
            )
        except Exception as exc:  # 单份整体失败（异常不应中断全部）
            print(f"    ⚠️ {fp.name} workflow 异常: {exc}", flush=True)
            findings = []
        non_compliant = [f for f in findings if f.get("verdict") not in ("compliant", "ok", "notApplicable", "", "unclear")]
        rule_n = sum(1 for f in non_compliant if is_rule_backed(f))
        print(f"    → 非合规判定 {len(non_compliant)} 条（其中规则兜底 {rule_n} 条）")
        results.append(
            {
                "file": fp.name,
                "raw_chars": raw_len,
                "truncated": truncated,
                "model": args.model,
                "provider": args.provider,
                "findings": [
                    {
                        "dimension": f.get("dimension"),
                        "verdict": f.get("verdict"),
                        "level": f.get("level"),
                        "clauseRef": f.get("clauseRef"),
                        "evidence": (
                            f.get("evidence", {}).get("text") if isinstance(f.get("evidence"), dict) else ""
                        ),
                        "description": f.get("description"),
                        "requirement_check": f.get("requirement_check"),
                        "rule_backed": is_rule_backed(f),
                        "needsHumanReview": f.get("needsHumanReview"),
                    }
                    for f in findings
                ],
            }
        )
        # ── 每跑完一份立即落盘（中断不丢进度）──
        out_json.write_text(json.dumps({"generated_at": datetime.now().isoformat(), "items": results}, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_report(args, results)
        print(f"    ✓ 已保存 {len(results)}/{len(files)} 份（{out_json}）", flush=True)

    # ── 最终落盘（幂等，覆盖式）──
    out_json = Path(args.out + "_results.json")
    out_json.write_text(json.dumps({"generated_at": datetime.now().isoformat(), "items": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md = _write_report(args, results)

    print("\n" + "=" * 60)
    print(f"JSON 报告: {out_json}")
    print(f"Markdown 报告（待人工复核）: {out_md}")
    print("复核模板见 docs/blind_test_plan.md §4；复核后更新面试话术。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
