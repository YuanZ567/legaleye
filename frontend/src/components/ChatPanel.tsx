/** 聊天栏（M7-1）：消费 SSE 任务事件流，展示任务状态/活跃节点/已用 token。
 *
 * 对齐 DESIGN 14.2 token：风险 #D92D20 / OK #12B76A / 低 #1570EF。
 * 接入 GET /tasks/{id}/events（经 useSSE）。
 */

import { useState } from "react";

import { useSSE } from "@/hooks/useSSE";

const DIMENSION_LABELS: Record<string, string> = {
  collection_agent: "收集",
  notice_consent_agent: "告知同意",
  purpose_minimization_agent: "目的最小化",
  third_party_agent: "第三方委托",
  cross_border_agent: "跨境",
  data_rights_agent: "权利响应",
  critic_agent: "Critic 复核",
};

export default function ChatPanel() {
  const [taskId, setTaskId] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<string[]>([]);

  const { status, activeNodes, tokenUsage, connected } = useSSE(taskId || null, {
    onEvent: (event) => {
      if (event.type === "nodeEnd") {
        const node = (event.data as { node?: string }).node ?? "";
        setMessages((prev) => [...prev, `[完成] ${DIMENSION_LABELS[node] ?? node}`]);
      }
    },
  });

  function send() {
    if (!input.trim()) return;
    setMessages((prev) => [...prev, `[你] ${input.trim()}`]);
    setInput("");
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-line-200 bg-surface">
      {/* 头部：连接状态 */}
      <div className="flex items-center gap-2 border-b border-line-200 px-4 py-3">
        <span
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: connected ? "#12B76A" : "#D92D20" }}
        />
        <span className="text-sm font-medium text-ink-900">
          {connected ? "审查进行中" : "等待任务"}
        </span>
        {status && (
          <span className="ml-auto text-xs text-ink-500">
            {status.status} · {status.progress}%
          </span>
        )}
      </div>

      {/* 任务 id 输入 */}
      <div className="flex gap-2 border-b border-line-200 px-4 py-2">
        <input
          className="h-8 flex-1 rounded border border-line-200 px-2 text-xs focus:outline-none"
          placeholder="输入任务 ID 连接 SSE"
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
        />
      </div>

      {/* 活跃节点 */}
      <div className="border-b border-line-200 px-4 py-2">
        <p className="mb-1 text-xs text-ink-500">活跃智能体</p>
        <div className="flex flex-wrap gap-1">
          {activeNodes.length === 0 ? (
            <span className="text-xs text-ink-400">无运行节点</span>
          ) : (
            activeNodes.map((n, i) => (
              <span
                key={i}
                className="rounded px-2 py-0.5 text-xs"
                style={{ backgroundColor: "#EFF8FF", color: "#1570EF" }}
              >
                {DIMENSION_LABELS[n.node] ?? n.node}
              </span>
            ))
          )}
        </div>
      </div>

      {/* 消息区 */}
      <div className="flex-1 space-y-2 overflow-y-auto px-4 py-3">
        {messages.length === 0 ? (
          <p className="text-xs text-ink-400">等待任务事件…（节点完成后显示进度）</p>
        ) : (
          messages.map((m, i) => (
            <div key={i} className="text-xs text-ink-700">
              {m}
            </div>
          ))
        )}
      </div>

      {/* 输入 + token 用量 */}
      <div className="border-t border-line-200 px-4 py-3">
        <div className="mb-2 flex items-center justify-between text-xs text-ink-500">
          <span>
            已用 token：
            <span className="font-medium" style={{ color: "#1570EF" }}>
              {(tokenUsage?.inputTokens ?? 0) + (tokenUsage?.outputTokens ?? 0)}
            </span>
          </span>
          <span>{tokenUsage?.model ?? "—"}</span>
        </div>
        <div className="flex gap-2">
          <input
            className="h-9 flex-1 rounded-md border border-line-200 px-3 text-sm focus:outline-none"
            placeholder="追问（带条款引用）…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button
            className="h-9 rounded-md bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700"
            onClick={send}
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
