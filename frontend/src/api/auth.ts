/** 认证 API（DATA_CONTRACT 4.1 Auth）：注册/登录/当前用户。 */

import { get, post } from "@/api/client";
import type { ApiResponse } from "@/api/client";
import type { AuthResponse, User } from "@/api/types";

/** POST /auth/register 注册。 */
export async function register(email: string, password: string): Promise<AuthResponse> {
  const resp = await post<ApiResponse<AuthResponse>>("/auth/register", { email, password });
  return resp.data;
}

/** POST /auth/login 登录。 */
export async function login(email: string, password: string): Promise<AuthResponse> {
  const resp = await post<ApiResponse<AuthResponse>>("/auth/login", { email, password });
  return resp.data;
}

/** GET /auth/me 当前用户。 */
export async function fetchMe(): Promise<User> {
  const resp = await get<ApiResponse<User>>("/auth/me");
  return resp.data;
}
