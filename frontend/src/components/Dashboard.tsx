/** 仪表盘（M7-4）：4 StatCard + 风险分布/维度发现/token 耗时条形。
 *
 * 对齐 DESIGN 14.2 token：风险 #D92D20 / OK #12B76A / 低 #1570EF。
 * 数据来自任务 SSE 状态与统计（运行中实时）。
 */

import type { TaskStatusEvent, TokenUsageEvent } from "@/api/types";

interface Props {
  status: TaskStatusEvent | null;
  tokenUsage: TokenUsageEvent | null;
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

export default function Dashboard({ status, tokenUsage }: Props) {
  const totalTokens =
    (tokenUsage?.inputTokens ?? 0) + (tokenUsage?.outputTokens ?? 0);
  const progress = status?.progress ?? 0;
  // 风险分布 mock：运行中示意（真实数据由任务 findings 聚合，M7-5 完善）
  const riskDist = [
    { label: "高风险", count: 1, color: HIGH },
    { label: "中风险", count: 3, color: "#DC6803" },
    { label: "低风险", count: 5, color: LOW },
  ];
  const maxRisk = Math.max(...riskDist.map((r) => r.count), 1);

  return (
    <div className="space-y-4">
      {/* 4 StatCard */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="任务进度" value={`${progress}%`} color={progress === 100 ? OK : LOW} />
        <StatCard label="任务状态" value={status?.status ?? "—"} color={status?.status === "done" ? OK : LOW} />
        <StatCard label="已用 token" value={String(totalTokens)} color={LOW} />
        <StatCard label="模型" value={tokenUsage?.model ?? "—"} color="#8A93A6" />
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
          输入 {tokenUsage?.inputTokens ?? 0} · 输出 {tokenUsage?.outputTokens ?? 0}
          （模型：{tokenUsage?.model ?? "待任务运行"}）
        </p>
      </div>
    </div>
  );
}
