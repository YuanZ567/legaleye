/** 报告 API（DATA_CONTRACT 4.9）：GET /reports/{taskId} + /export.md。 */

import { get } from "@/api/client";
import type { Report } from "@/api/types";

/** 后端地址（与 client.ts 保持一致）。 */
const BASE_URL = "http://localhost:8000";

/** GET /reports/{taskId} 拉取报告 JSON。 */
export async function fetchReport(taskId: string): Promise<Report> {
  const resp = await get<{ data: Report }>(`/reports/${taskId}`);
  return resp.data;
}

/** GET /reports/{taskId}/export.md 导出 Markdown 的下载链接。 */
export function reportMarkdownUrl(taskId: string): string {
  return `${BASE_URL}/reports/${taskId}/export.md`;
}
