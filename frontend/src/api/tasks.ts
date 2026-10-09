/** 任务 API（DATA_CONTRACT 4.4）：列表/创建/删除。 */

import { del, get, post, type ApiResponse } from "@/api/client";
import type { ReviewTask } from "@/api/types";

/** GET /tasks 任务列表（可按 status 筛选）。 */
export async function fetchTasks(status?: string): Promise<ReviewTask[]> {
  const qs = status && status !== "all" ? `?status=${status}` : "";
  const resp = await get<ApiResponse<ReviewTask[]>>(`/tasks${qs}`);
  return resp.data;
}

/** POST /tasks 创建审查任务（分发 Celery；返回 taskId）。
 * 兼容两种返回：{"taskId"}（裸）与 {"data":{"taskId"}}（包裹）。 */
export async function createTask(
  documentIds: string[],
  taskType = "compliance",
): Promise<string> {
  const body = await post<{ data?: { taskId?: string }; taskId?: string }>("/tasks", {
    documentIds,
    taskType,
  });
  const taskId = body.data?.taskId ?? body.taskId;
  if (!taskId) throw new Error("创建接口未返回 taskId");
  return taskId;
}

/** GET /tasks/{id} 任务详情（含 documentId / status）。 */
export async function fetchTask(id: string): Promise<ReviewTask> {
  const resp = await get<ApiResponse<ReviewTask>>(`/tasks/${id}`);
  return resp.data;
}

/** DELETE /tasks/{id} 删除任务（admin；级联删除 findings + report）。 */
export async function deleteTask(id: string): Promise<void> {
  await del<{ deleted: boolean }>(`/tasks/${id}`);
}
