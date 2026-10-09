/** 仪表盘（M7-4；M10+ 接真实数据）：4 StatCard + 风险分布/维度发现/token 耗时条形。
 *
 * 数据来源双通道：运行中走 SSE 实时事件；任务详情/报告加载后显示真实聚合
 * （风险分布按 findings.level 统计，替代原 mock）。
 */

import type { ReviewTask, TaskStatusEvent, TokenUsageEvent } from "@/api/types";

interface RiskCounts {
  high: number;
  medium: number;
  low: number;
}

interface Props {
  status: TaskStatusEvent | null;
  tokenUsage: TokenUsageEvent | null;
  /** 任务详情（详情深链时提供；SSE 无事件时兜底展示终态）。 */
  task?: ReviewTask | null;
  /** 报告聚合的风险分布（报告就绪后提供）。 */
  risk?: RiskCounts | null;
}

const HIGH = "#D92D20";
const OK = "#12B76A";
const LOW = "#1570EF";

function StatCard({
  label, value, color,
}: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border border-line-200 bg-surface px-4 py-3">
      <p className="text-xs text-ink-500">{label}</p>
      <p className="mt-1 text-xl font-semibold" style={{ color }}>
        {value}
      </p>
    </div>
  );
}

export default function Dashboard({ status, tokenUsage, task, risk }: Props) {
  // SSE 实时优先，任务详情兜底（SSE 对已完成任务不再回放事件）。
  // 进度取两者最大值：SSE 队列可能滞留旧事件（如任务启动时的 10%），
  // 后连的 SSE 会先收到旧事件，取 max 防止进度倒挂回退。
  const progress = Math.max(status?.progress ?? 0, task?.progress ?? 0);
  const statusText = status?.status ?? task?.status ?? "—";
  const inputTokens = tokenUsage?.inputTokens ?? 0;
  const outputTokens = tokenUsage?.outputTokens ?? 0;
  const hasLiveTokens = tokenUsage !== null;
  const totalTokens = hasLiveTokens
    ? inputTokens + outputTokens
    : (task?.tokenUsage ?? 0);

  // 风险分布：报告 findings 按 level 聚合（真实数据；无报告时全 0）
  const riskDist = [
    { label: "高风险", count: risk?.high ?? 0, color: HIGH },
    { label: "中风险", count: risk?.medium ?? 0, color: "#DC6803" },
    { label: "低风险", count: risk?.low ?? 0, color: LOW },
  ];
  const maxRisk = Math.max(...riskDist.map((r) => r.count), 1);

  return (
    <div className="space-y-4">
      {/* 4 StatCard */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="任务进度" value={`${progress}%`} color={progress === 100 ? OK : LOW} />
        <StatCard label="任务状态" value={statusText} color={statusText === "done" ? OK : LOW} />
        <StatCard label="已用 token" value={String(totalTokens)} color={LOW} />
        <StatCard label="模型" value={tokenUsage?.model ?? (task ? "已归档" : "—")} color="#8A93A6" />
      </div>

      {/* 风险分布 */}
      <div className="rounded-lg border border-line-200 bg-surface p-4">
        <p className="mb-3 text-sm font-medium text-ink-900">风险分布</p>
        <div className="space-y-2">
          {riskDist.map((r) => (
            <div key={r.label} className="flex items-center gap-3">
              <span className="w-16 text-xs text-ink-500">{r.label}</span>
              <div className="h-3 flex-1 overflow-hidden rounded bg-muted">
                <div
                  className="h-full rounded"
                  style={{
                    width: `${(r.count / maxRisk) * 100}%`,
                    backgroundColor: r.color,
                  }}
                />
              </div>
              <span className="w-8 text-right text-xs text-ink-600">{r.count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* token 用量 */}
      <div className="rounded-lg border border-line-200 bg-surface p-4">
        <p className="mb-2 text-sm font-medium text-ink-900">Token 用量</p>
        <p className="text-xs text-ink-600">
          {hasLiveTokens
            ? `输入 ${inputTokens} · 输出 ${outputTokens}（模型：${tokenUsage?.model ?? "待任务运行"}）`
            : task
              ? `任务累计消耗 ${task.tokenUsage} tokens（明细仅在任务运行时实时记录）`
              : "输入 0 · 输出 0（待任务运行）"}
        </p>
      </div>
    </div>
  );
}
