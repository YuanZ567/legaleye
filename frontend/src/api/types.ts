/** API 数据类型（对齐 DATA_CONTRACT 3.3 SSE 事件 + 4.4 任务）。 */

/** SSE 四类事件类型（DATA_CONTRACT 3.3）。 */
export type SSEEventType =
  | "taskStatus"
  | "nodeStart"
  | "nodeEnd"
  | "tokenUsage";

/** taskStatus 事件载荷。 */
export interface TaskStatusEvent {
  status: "queued" | "running" | "done" | "failed" | "degraded";
  progress: number;
  findingCount?: number;
}

/** nodeStart/nodeEnd 事件载荷。 */
export interface NodeEvent {
  node: string;
  dimension?: string;
  degraded?: boolean;
}

/** tokenUsage 事件载荷。 */
export interface TokenUsageEvent {
  provider: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
}

/** 通用 SSE 事件。 */
export interface SSEEvent {
  type: SSEEventType;
  data: TaskStatusEvent | NodeEvent | TokenUsageEvent;
}

/** 审查任务（DATA_CONTRACT 4.4 核心）。 */
export interface ReviewTask {
  id: string;
  status: string;
  progress: number;
  tokenUsage: number;
  findingCount: number;
  error?: string | null;
}
