/** 图谱 API：GET /documents/{id}/graph（对齐 DATA_CONTRACT 4.7 GraphPayload）。 */

import { get } from "./client";

export type EntityRole =
  | "controller"
  | "processor"
  | "trustee"
  | "overseasReceiver"
  | "dataCategory";

export type EdgeType =
  | "collect"
  | "store"
  | "share"
  | "entrust"
  | "crossBorder"
  | "anonymize";

export type RiskLevel = "high" | "medium" | "low" | "ok" | "pending";

export interface GraphEntity {
  id: string;
  name: string;
  role: EntityRole;
  isSensitive?: boolean;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  type: EdgeType;
  legalBasis?: string | null;
  isRisk?: boolean;
}

export interface RiskPath {
  id: string;
  path: string[];
  edges: string[];
  reason: string;
  level: RiskLevel;
}

export interface Suggestion {
  pathType: "securityAssessment" | "scc" | "certification" | "unknown";
  advice: string;
  level: RiskLevel;
}

export interface GraphPayload {
  entities: GraphEntity[];
  edges: GraphEdge[];
  riskPaths: RiskPath[];
  suggestions: Suggestion[];
}

/** 拉取指定文档的数据流图谱（含 R1-R4 riskPaths/suggestions）。 */
export async function fetchDocumentGraph(documentId: string): Promise<GraphPayload> {
  const resp = await get<{ data: GraphPayload }>(`/documents/${documentId}/graph`);
  return resp.data;
}
