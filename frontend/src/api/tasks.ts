/** 任务 API（DATA_CONTRACT 4.4）：列表/创建/详情。 */

import { get, type ApiResponse } from "@/api/client";
import type { ReviewTask } from "@/api/types";

/** GET /tasks 任务列表（可按 status 筛选）。 */
export async function fetchTasks(status?: string): Promise<ReviewTask[]> {
  const qs = status && status !== "all" ? `?status=${status}` : "";
  const resp = await get<ApiResponse<ReviewTask[]>>(`/tasks${qs}`);
  return resp.data;
}
