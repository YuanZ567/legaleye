import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { MainLayout } from "@/components/MainLayout";
import RequireAuth from "@/components/RequireAuth";
import Login from "@/pages/Login";
import OAuthCallback from "@/pages/OAuthCallback";

/** 路由（M9-6；M10+ 补任务/报告深链）：
 * - /login 独立全屏；/oauth/callback 回调；
 * - / 主界面；/tasks/:taskId 任务列表（深链）；/reports/:taskId 直接打开报告；
 * - * 兜底回主界面，避免 react-router 裸 404 错误页。
 * MainLayout 内部按 pathname 派生初始视图，深链与侧边栏导航共用一套布局。
 */
const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/oauth/callback", element: <OAuthCallback /> },
  {
    element: <RequireAuth />,
    children: [
      { path: "/", element: <MainLayout /> },
      { path: "/tasks/new", element: <MainLayout /> },
      { path: "/tasks/:taskId", element: <MainLayout /> },
      { path: "/reports/:taskId", element: <MainLayout /> },
      { path: "*", element: <MainLayout /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
