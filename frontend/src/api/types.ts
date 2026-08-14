/** API 数据类型（对齐 DATA_CONTRACT 3.3 SSE 事件 + 4.4 任务）。 */

/** SSE 四类事件类型（DATA_CONTRACT 3.3）。 */
export type SSEEventType = "taskStatus" | "nodeStart" | "nodeEnd" | "tokenUsage";

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

/** 风险等级（DATA_CONTRACT 3.1 RiskLevel）。 */
export type RiskLevel = "high" | "medium" | "low" | "ok" | "pending";

/** 审查维度（DATA_CONTRACT 3.1 Dimension）。 */
export type Dimension = "D1" | "D2" | "D3" | "D4" | "D5" | "D6" | "crossConsistency";

/** 审查结论（DATA_CONTRACT 4.8 ComplianceFinding 完整契约，含 evidence）。 */
export interface FindingContract {
  id: string;
  taskId?: string | null;
  dimension: Dimension;
  verdict: string;
  level: RiskLevel;
  clauseRef: string;
  statuteVersion?: string | null;
  description: string;
  remediation: string;
  confidence: number;
  needsHumanReview: boolean;
  evidence?: { text: string; charRange: [number, number] } | null;
}

/** 跨文档单侧声明（DATA_CONTRACT 4.8 DocDeclaration）。 */
export interface DocDeclaration {
  documentId: string;
  value: string;
  evidence?: { text: string; charRange: [number, number] } | null;
}

/** 跨文档矛盾（DATA_CONTRACT 4.8 CrossDocConflict）。 */
export interface CrossDocConflict {
  id: string;
  taskId?: string | null;
  declarationKey: string;
  docA: DocDeclaration;
  docB: DocDeclaration;
  level: RiskLevel;
}

/** 合规报告（DATA_CONTRACT 4.9 Report）。 */
export interface Report {
  taskId: string;
  summary: string;
  baselineVersion: string;
  generatedAt: string;
  findingCount: number;
  highRiskCount: number;
  findings: FindingContract[];
  crossDocConflicts?: CrossDocConflict[];
}
