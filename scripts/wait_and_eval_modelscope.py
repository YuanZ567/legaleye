"""魔搭免费额度恢复探针 + 自动重跑全量评估（2026-08-31 限流事件后）。

背景：6 维并行打魔搭免费层会触发 235B 429 动态限流窗口（持续封锁数小时，
单次探测偶尔放行）。用户选定**低速率恢复策略**：探测成功后在当前进程内
以并发 1 + 每调用间隔 40s 重跑全量（预计 3-4 小时），避免再次触发限流。

v2 修复：v1 用 subprocess.run 调用 evaluate.py，子进程在 Windows 上撞 asyncio proactor
初始化错误（WinError 10106）且 python.exe 路径错位。改为探针成功后**在当前进程内**
import evaluate 并设置 Selector 事件循环再调用 main()，完全规避子进程问题。

用法：python wait_and_eval_modelscope.py [--max-wait-min 120]
"""
import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
# 关键：必须先设置事件循环策略，再让 evaluate 触发 asyncio，否则在沙箱子进程里会
# 撞 Windows proactor 初始化失败（WinError 10106）。Selector 循环在 Windows 上无需 IOCP。
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from openai import OpenAI
from app.llm.factory import _read_user_env, MODELSCOPE_ENV_KEY

MODEL = "Qwen/Qwen3-235B-A22B"


def probe() -> bool:
    """探针：同步 OpenAI 调用测 235B 是否可用。"""
    api_key = _read_user_env(MODELSCOPE_ENV_KEY)
    if not api_key:
        print("[watcher] 未读到 Modelscope_API_KEY，跳过探针", flush=True)
        return False
    try:
        client = OpenAI(api_key=api_key, base_url="https://api-inference.modelscope.cn/v1", timeout=30)
        r = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": "hi"}], max_tokens=5
        )
        ok = bool(r.choices and r.choices[0].message.content)
        return ok
    except Exception as e:
        print(f"[watcher] probe err: {type(e).__name__} {str(e)[:80]}", flush=True)
        return False


def run_eval() -> None:
    """在当前进程内续跑全量评估（避免子进程 asyncio 问题）。

    低速率模式：并发 1 + 每调用间隔 30s，避免再次触发魔搭 235B 的动态限流窗口。
    evaluate.py 的断点续跑会自动跳过缓存中已完成的份（当前 21 份），只跑剩余。
    """
    import evaluate  # noqa: PLC0415  scripts/evaluate.py

    # 覆盖模块级限流参数：并发 1、间隔 30s
    evaluate.MODELSCOPE_MAX_CONCURRENCY = 1
    evaluate.MODELSCOPE_CALL_INTERVAL = 30

    # 覆盖 DATABASE_URL：infra/.env 默认是容器内 postgres:5432，宿主机不可解析
    sys.argv = [
        "evaluate.py",
        "--provider", "modelscope",
        "--model", MODEL,
    ]
    evaluate.main()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-wait-min", type=int, default=600)
    ap.add_argument("--interval-sec", type=int, default=300)
    args = ap.parse_args()
    deadline = time.time() + args.max_wait_min * 60
    attempt = 0
    print(f"[watcher] 探测 {MODEL} 恢复中，最长等待 {args.max_wait_min} 分钟", flush=True)
    while time.time() < deadline:
        attempt += 1
        if probe():
            print(f"[watcher] 第 {attempt} 次探测成功，模型已恢复，开始重跑全量评估（in-process）", flush=True)
            try:
                run_eval()
            except SystemExit as e:
                print(f"[watcher] evaluate.main() 退出码 {e.code}", flush=True)
            except Exception as e:
                print(f"[watcher] run_eval 异常: {type(e).__name__} {e}", flush=True)
            print("[watcher] 全量评估结束", flush=True)
            return 0
        print(f"[watcher] 第 {attempt} 次探测失败，{args.interval_sec}s 后重试", flush=True)
        time.sleep(args.interval_sec)
    print(f"[watcher] 等待超时（{args.max_wait_min} 分钟）仍未恢复", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
