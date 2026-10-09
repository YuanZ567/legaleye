/** 文档 API（DATA_CONTRACT 4.3）：上传（multipart）/ 文档信息。 */

import { upload, type ApiResponse } from "@/api/client";

/** 文档（对齐后端 DocumentOut）。 */
export interface DocumentInfo {
  id: string;
  filename: string;
  docType: "privacyPolicy" | "userAgreement" | "dpa" | "scc";
  charCount: number;
  textPreview: string | null;
  sensitiveMode: boolean;
  createdAt: string;
}

/** POST /documents 上传合规文档（multipart：file + docType? + sensitiveMode?）。 */
export async function uploadDocument(
  file: File,
  docType?: string,
  sensitiveMode?: boolean,
): Promise<DocumentInfo> {
  const formData = new FormData();
  formData.append("file", file);
  if (docType) formData.append("docType", docType);
  if (sensitiveMode !== undefined) formData.append("sensitiveMode", String(sensitiveMode));
  const resp = await upload<ApiResponse<DocumentInfo>>("/documents", formData);
  return resp.data;
}
