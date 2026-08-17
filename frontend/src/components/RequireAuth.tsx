/** 路由守卫（M9-6）：未登录强制跳 /login。 */

import { Navigate, Outlet } from "react-router-dom";

import { getToken } from "@/api/client";

export default function RequireAuth() {
  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}
