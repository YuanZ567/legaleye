/** 任务列表页（M8-4）：表格 + 状态筛选 + 状态 Badge + 新建入口。
 *
 * 对齐 DESIGN 14.2 token：queued 灰 / running 蓝 #1570EF / done 绿 #12B76A / failed 红 #D92D20。
 */

import { useCallback, useEffect, useState } from "react";

import { fetchTasks } from "@/api/tasks";
import type { ReviewTask } from "@/api/types";

const STATUS_COLOR: Record<string, string> = {
  queued: "#8A93A6",
  running: "#1570EF",
  done: "#12B76A",
  failed: "#D92D20",
  degraded: "#DC6803",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ backgroundColor: `${STATUS_COLOR[status] ?? "#8A93A6"}1A`, color: STATUS_COLOR[status] ?? "#8A93A6" }}
    >
      {status}
    </span>
  );
}

const STATUS_OPTIONS = ["all", "queued", "running", "done", "failed"];

export default function TaskList() {
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchTasks(filter);
      setTasks(data);
    } catch {
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      {/* 工具栏：筛选 + 新建入口 */}
      <div className="flex items-center gap-3">
        <div className="flex gap-1">
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`rounded-md px-3 py-1.5 text-sm ${
                filter === s ? "bg-brand-50 font-medium text-brand-700" : "text-ink-600 hover:bg-muted"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <button className="ml-auto rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          + 新建审查
        </button>
      </div>

      {/* 任务表格 */}
      <div className="overflow-hidden rounded-lg border border-line-200 bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line-200 bg-muted">
            <tr>
              <th className="px-4 py-3 font-medium text-ink-500">ID</th>
              <th className="px-4 py-3 font-medium text-ink-500">状态</th>
              <th className="px-4 py-3 font-medium text-ink-500">进度</th>
              <th className="px-4 py-3 font-medium text-ink-500">Findings</th>
              <th className="px-4 py-3 font-medium text-ink-500">Token</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-ink-400">
                  加载中…
                </td>
              </tr>
            )}
            {!loading && tasks.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-ink-400">
                  暂无任务
                </td>
              </tr>
            )}
            {!loading &&
              tasks.map((t) => (
                <tr key={t.id} className="border-b border-line-100 last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-3 font-mono text-xs text-ink-500">{t.id.slice(0, 8)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={t.status} />
                  </td>
                  <td className="px-4 py-3 text-ink-700">{t.progress}%</td>
                  <td className="px-4 py-3 text-ink-700">{t.findingCount}</td>
                  <td className="px-4 py-3 text-ink-700">{t.tokenUsage}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
