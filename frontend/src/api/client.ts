/** API 基础客户端：统一 fetch 封装（JSON + 错误处理 + JWT 自动附加）。 */

// 后端地址（本地开发默认 8000；容器内由环境注入）
const BASE_URL = "http://localhost:8000";

/** JWT 存储键（M8 账号；登录成功后写入 localStorage）。 */
export const AUTH_TOKEN_KEY = "legaleye_token";

/** 当前用户存储键（含 role，供前端菜单鉴权）。 */
export const AUTH_USER_KEY = "legaleye_user";

/** 全局登出事件：401 或手动退出时派发，App 监听后跳登录页。 */
export const AUTH_LOGOUT_EVENT = "auth:logout";

/** 读取当前登录 token（未登录返回 null）。 */
export function getToken(): string | null {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

/** 读取当前登录用户（未登录返回 null）。 */
export function getUser<T = { role?: string }>(): T | null {
  const raw = localStorage.getItem(AUTH_USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

/** 保存登录态（token + user）。 */
export function saveAuth(token: string, user: unknown): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

/** 清除登录态并通知全局（跳登录页）。 */
export function clearAuth(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
  window.dispatchEvent(new Event(AUTH_LOGOUT_EVENT));
}

/** 更新本地存储的当前用户（改资料/头像后同步，token 不变）。 */
export function updateStoredUser(user: unknown): void {
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

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
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers,
  });
  if (!resp.ok) {
    let detail = `请求失败 (${resp.status})`;
    try {
      const body = await resp.json();
      detail = body?.error?.message ?? detail;
    } catch {
      // 非 JSON 响应，保留默认错误
    }
    // 401 统一处理：仅当是"已带 token 的请求"才触发全局登出
    // （登录/注册接口自身的 401 是"密码错误"，不应触发跳转）
    if (resp.status === 401 && token) {
      clearAuth();
    }
    throw new ApiError(detail, resp.status === 401 ? "unauthorized" : "unknown");
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

export async function put<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export async function patch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** multipart 上传：自动附加 JWT；禁止手动设置 Content-Type（浏览器自动生成 boundary）。 */
export async function upload<T>(path: string, formData: FormData): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`${BASE_URL}${path}`, { method: "POST", headers, body: formData });
  if (!resp.ok) {
    let detail = `请求失败 (${resp.status})`;
    try {
      const body = await resp.json();
      detail = body?.error?.message ?? detail;
    } catch {
      // 非 JSON 响应，保留默认错误
    }
    throw new ApiError(detail, resp.status === 401 ? "unauthorized" : "unknown");
  }
  return (await resp.json()) as T;
}

export async function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

/** 文件下载：带 JWT 的 GET，响应转 blob 触发浏览器下载（attachment 类接口）。
 *
 * M10 修复：报告导出原来是 <a href> 直跳后端，不带 Authorization 头 → 401 导不出。
 */
export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`${BASE_URL}${path}`, { method: "GET", headers });
  if (!resp.ok) {
    let detail = `下载失败 (${resp.status})`;
    try {
      const body = await resp.json();
      detail = body?.error?.message ?? body?.detail ?? detail;
    } catch {
      // 非 JSON 响应，保留默认错误
    }
    throw new ApiError(detail, resp.status === 401 ? "unauthorized" : "unknown");
  }
  const blob = await resp.blob();
  // 优先用服务端 Content-Disposition 的文件名
  const dispo = resp.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/i.exec(dispo);
  const name = match?.[1] ?? fallbackName;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
