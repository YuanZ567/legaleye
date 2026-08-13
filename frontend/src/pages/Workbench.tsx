/** 审查工作台（M7-5）：四栏同页实时联动（聊天 / 编排画布 / 数据流图谱 / 仪表盘）。
 *
 * 共享同一 taskId 的 SSE 事件流，四栏实时更新：
 *  - 聊天栏：任务状态/节点完成/token；
 *  - 编排画布：节点状态着色（running/done）；
 *  - 数据流图谱：运行中图谱更新（M3-5 GraphPreview）；
 *  - 仪表盘：进度/风险分布/token 实时。
 */

import { useState } from "react";

import ChatPanel from "@/components/ChatPanel";
import Dashboard from "@/components/Dashboard";
import OrchestrationCanvas from "@/components/OrchestrationCanvas";
import { useSSE } from "@/hooks/useSSE";
import GraphPreview from "@/pages/GraphPreview";

export default function Workbench() {
  const [taskId, setTaskId] = useState("");
  const { status, activeNodes, tokenUsage, connected } = useSSE(taskId || null);
  const [graphDocId, setGraphDocId] = useState("");

  return (
    <div className="space-y-4">
      {/* 任务连接栏 */}
      <div className="flex items-center gap-3 rounded-lg border border-line-200 bg-surface px-4 py-3">
        <span
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: connected ? "#12B76A" : "#D92D20" }}
        />
        <span className="text-sm font-medium text-ink-900">
          {connected ? "已连接" : "未连接"}
        </span>
        <input
          className="h-8 w-72 rounded border border-line-200 px-2 text-xs focus:outline-none"
          placeholder="任务 ID（SSE）"
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
        />
        <input
          className="h-8 w-72 rounded border border-line-200 px-2 text-xs focus:outline-none"
          placeholder="文档 ID（图谱）"
          value={graphDocId}
          onChange={(e) => setGraphDocId(e.target.value)}
        />
        <span className="ml-auto text-xs text-ink-500">
          {status?.status ?? "—"} · {status?.progress ?? 0}%
        </span>
      </div>

      {/* 四栏联动：左聊天 + 右（画布/仪表盘/图谱） */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        {/* 聊天栏（1 栏） */}
        <div className="lg:col-span-1">
          <ChatPanel />
        </div>

        {/* 右侧三块 */}
        <div className="space-y-4 lg:col-span-3">
          {/* 仪表盘 */}
          <Dashboard status={status} tokenUsage={tokenUsage} />

          {/* 编排画布 + 数据流图谱并排 */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <OrchestrationCanvas activeNodes={activeNodes} done={status?.status === "done"} />
            <div className="rounded-lg border border-line-200 bg-paper p-2">
              {graphDocId ? (
                <GraphPreview initialDocId={graphDocId} />
              ) : (
                <p className="flex h-[520px] items-center justify-center text-sm text-ink-400">
                  输入文档 ID 渲染数据流图谱
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
