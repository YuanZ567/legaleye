/** 知识库 API（DATA_CONTRACT 4.10）：法条列表 + 语义检索。 */

import { get, post } from "@/api/client";
import type { ApiResponse } from "@/api/client";
import type { LawBaseline, LawSearchHit } from "@/api/types";

/** 添加法条请求（M9-7 admin）。 */
export interface CreateLawIn {
  statute: string;
  articleNo: string;
  articleText: string;
  effectiveDate: string;
  source: string;
  version?: string;
}

/** GET /knowledge/laws 法条列表（可 statute/version 过滤）。 */
export async function fetchLaws(statute?: string, version?: string): Promise<LawBaseline[]> {
  const qs = new URLSearchParams();
  if (statute) qs.set("statute", statute);
  if (version) qs.set("version", version);
  const q = qs.toString();
  const resp = await get<ApiResponse<LawBaseline[]>>(`/knowledge/laws${q ? `?${q}` : ""}`);
  return resp.data;
}

/** POST /knowledge/laws/search 语义检索 Top-5。 */
export async function searchLaws(query: string): Promise<LawSearchHit[]> {
  const resp = await post<ApiResponse<{ results: LawSearchHit[] }>>("/knowledge/laws/search", {
    query,
  });
  return resp.data.results;
}

/** POST /knowledge/laws 添加法条（admin；生成 embedding 后入库）。 */
export async function createLaw(payload: CreateLawIn): Promise<LawBaseline> {
  const resp = await post<ApiResponse<LawBaseline>>("/knowledge/laws", payload);
  return resp.data;
}
