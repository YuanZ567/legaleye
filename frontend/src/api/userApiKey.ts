/** 用户级 API Key API（M9-8）：设置/清除自己的 Key。 */

import { del, put, type ApiResponse } from "@/api/client";

/** PUT /users/me/api-key {apiKey} → {apiKeyTail}。 */
export async function setMyApiKey(apiKey: string): Promise<string> {
  const resp = await put<ApiResponse<{ apiKeyTail: string }>>("/users/me/api-key", {
    apiKey,
  });
  return resp.data.apiKeyTail;
}

/** DELETE /users/me/api-key → 清除。 */
export async function clearMyApiKey(): Promise<void> {
  await del<ApiResponse<{ cleared: boolean }>>("/users/me/api-key");
}
