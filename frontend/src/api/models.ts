/** 模型配置 API（DATA_CONTRACT 4.2 Models）：列表/新增/激活/测试。 */

import { get, post, put } from "@/api/client";
import type { ApiResponse } from "@/api/client";
import type { ModelConfig, ModelTestOut, Provider } from "@/api/types";

/** GET /models 列出全部模型（Key 脱敏 apiKeyTail）。 */
export async function fetchModels(): Promise<ModelConfig[]> {
  const resp = await get<ApiResponse<ModelConfig[]>>("/models");
  return resp.data;
}

/** POST /models 新增模型（Key 会 Fernet 密文存储）。 */
export async function createModel(
  provider: Provider,
  apiKey: string,
  model: string,
): Promise<ModelConfig> {
  const resp = await post<ApiResponse<ModelConfig>>("/models", { provider, apiKey, model });
  return resp.data;
}

/** POST /models/test 真实验证打通 provider（保存前拦截无效 Key）。 */
export async function testModel(
  provider: Provider,
  apiKey: string,
  model: string,
): Promise<ModelTestOut> {
  const resp = await post<ApiResponse<ModelTestOut>>("/models/test", {
    provider,
    apiKey,
    model,
  });
  return resp.data;
}

/** PUT /models/{id}/activate 切换激活。 */
export async function activateModel(id: string): Promise<ModelConfig> {
  const resp = await put<ApiResponse<ModelConfig>>(`/models/${id}/activate`);
  return resp.data;
}
