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

/** 用户角色（DATA_CONTRACT 3.1 UserRole）。 */
export type UserRole = "user" | "admin";

/** 用户（DATA_CONTRACT 4.1 UserOut）。 */
export interface User {
  id: string;
  email: string;
  role: UserRole;
  createdAt: string;
  /** 用户级 API Key 尾号（M9-8；未配置 → null；展示格式 ****abcd）。 */
  apiKeyTail?: string | null;
}

/** 认证响应（DATA_CONTRACT 4.1 AuthOut）：{token, user}。 */
export interface AuthResponse {
  token: string;
  user: User;
}

/** LLM Provider（DATA_CONTRACT 3.1 Provider）。 */
export type Provider = "bailian" | "deepseek" | "openai" | "anthropic";

export const PROVIDERS: Provider[] = ["bailian", "deepseek", "openai", "anthropic"];

/** 模型配置（DATA_CONTRACT 4.2 ModelConfig）：Key 仅 apiKeyTail 末 4 位。 */
export interface ModelConfig {
  id: string;
  provider: Provider;
  displayName: string;
  model: string;
  apiKeyTail: string;
  isActive: boolean;
}

/** 模型测试响应（DATA_CONTRACT 4.2 ModelTestOut）：{ok, message?}。 */
export interface ModelTestOut {
  ok: boolean;
  message?: string | null;
}

/** 法条基线（DATA_CONTRACT 4.10 LawBaseline）。 */
export interface LawBaseline {
  id: string;
  statute: string;
  articleNo: string;
  articleText: string;
  effectiveDate: string;
  version: string;
  source: string;
  createdAt: string;
}

/** 法条检索命中（DATA_CONTRACT 4.10 LawSearchHit）。 */
export interface LawSearchHit {
  clauseRef: string;
  statuteVersion: string;
  articleText: string;
  score: number;
}
