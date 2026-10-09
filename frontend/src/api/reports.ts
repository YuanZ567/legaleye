/** 报告 API（DATA_CONTRACT 4.9）：GET /reports/{taskId} + /export.md。 */

import { downloadFile, get } from "@/api/client";
import type { Report } from "@/api/types";

/** GET /reports/{taskId} 拉取报告 JSON。 */
export async function fetchReport(taskId: string): Promise<Report> {
  const resp = await get<{ data: Report }>(`/reports/${taskId}`);
  return resp.data;
}

/** GET /reports/{taskId}/export.md 导出 Markdown（带 JWT 的 blob 下载，M10 修复 401）。 */
export function exportReportMarkdown(taskId: string): Promise<void> {
  return downloadFile(`/reports/${taskId}/export.md`, `report-${taskId}.md`);
}
