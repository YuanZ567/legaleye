/** 认证 API（DATA_CONTRACT 4.1 Auth）：注册/登录/当前用户 + 账户管理。 */

import { get, patch, post } from "@/api/client";
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

/** PATCH /auth/me 更新资料（显示名/头像；均可选，至少一项）。 */
export async function updateProfile(
  patchData: { displayName?: string | null; avatar?: string | null },
): Promise<User> {
  const resp = await patch<ApiResponse<User>>("/auth/me", patchData);
  return resp.data;
}

/** POST /auth/change-password 已登录改密（需旧密码）。 */
export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await post<ApiResponse<{ ok: boolean }>>("/auth/change-password", {
    oldPassword,
    newPassword,
  });
}

/** POST /auth/reset-password 忘记密码：按注册邮箱重置。 */
export async function resetPassword(email: string, newPassword: string): Promise<void> {
  await post<ApiResponse<{ ok: boolean }>>("/auth/reset-password", { email, newPassword });
}
