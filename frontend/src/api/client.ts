/** API 基础客户端：统一 fetch 封装（JSON + 错误处理）。 */

// 后端地址（本地开发默认 8000；容器内由环境注入）
const BASE_URL = "http://localhost:8000";

/** API 统一响应包裹：{data: T}。 */
export interface ApiResponse<T> {
  data: T;
}

export class ApiError extends Error {
  code: string;

  constructor(message: string, code = "unknown") {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!resp.ok) {
    let detail = `请求失败 (${resp.status})`;
    try {
      const body = await resp.json();
      detail = body?.error?.message ?? detail;
    } catch {
      // 非 JSON 响应，保留默认错误
    }
    throw new ApiError(detail);
  }
  return (await resp.json()) as T;
}

export async function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
