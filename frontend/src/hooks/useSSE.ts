/** SSE 事件消费 hook：连接 GET /tasks/{id}/events，解析四类事件（DATA_CONTRACT 3.3）。
 *
 * 事件名映射：taskStatus / nodeStart / nodeEnd / tokenUsage。
 * 后端地址与 api/client 一致。
 */

import { useCallback, useEffect, useRef, useState } from "react";

import type {
  NodeEvent,
  SSEEvent,
  TaskStatusEvent,
  TokenUsageEvent,
} from "@/api/types";

const BASE_URL = "http://localhost:8000";

export interface UseSSEOptions {
  /** 是否自动连接（默认 true）。 */
  enabled?: boolean;
  /** 事件到达回调（实时消费）。 */
  onEvent?: (event: SSEEvent) => void;
}

export interface UseSSEResult {
  /** 最近一次任务状态。 */
  status: TaskStatusEvent | null;
  /** 当前活跃节点列表。 */
  activeNodes: NodeEvent[];
  /** 累计 token 用量。 */
  tokenUsage: TokenUsageEvent | null;
  /** 连接是否建立。 */
  connected: boolean;
  /** 手动重连。 */
  reconnect: () => void;
}

export function useSSE(taskId: string | null, options: UseSSEOptions = {}): UseSSEResult {
  const { enabled = true, onEvent } = options;
  const [status, setStatus] = useState<TaskStatusEvent | null>(null);
  const [activeNodes, setActiveNodes] = useState<NodeEvent[]>([]);
  const [tokenUsage, setTokenUsage] = useState<TokenUsageEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!taskId) return;
    esRef.current?.close();

    const es = new EventSource(`${BASE_URL}/tasks/${taskId}/events`);
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => {
      // EventSource 自动重连；短暂标记断开
      setConnected(false);
    };
    es.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as SSEEvent;
        switch (event.type) {
          case "taskStatus":
            setStatus(event.data as TaskStatusEvent);
            break;
          case "nodeStart":
            setActiveNodes((prev) => [...prev, event.data as NodeEvent]);
            break;
          case "nodeEnd":
            setActiveNodes((prev) =>
              prev.filter((n) => n.node !== (event.data as NodeEvent).node),
            );
            break;
          case "tokenUsage":
            setTokenUsage(event.data as TokenUsageEvent);
            break;
        }
        onEventRef.current?.(event);
      } catch {
        // 忽略无法解析的事件（keepalive 注释等）
      }
    };
  }, [taskId]);

  useEffect(() => {
    if (!enabled || !taskId) return;
    connect();
    return () => {
      esRef.current?.close();
      esRef.current = null;
    };
  }, [enabled, taskId, connect]);

  const reconnect = useCallback(() => connect(), [connect]);

  return { status, activeNodes, tokenUsage, connected, reconnect };
}
