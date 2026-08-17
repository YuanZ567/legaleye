import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { MainLayout } from "@/components/MainLayout";
import RequireAuth from "@/components/RequireAuth";
import Login from "@/pages/Login";
import OAuthCallback from "@/pages/OAuthCallback";

/** M9-6 路由：/login 独立全屏；/oauth/callback 回调；/ 需登录主界面。 */
const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/oauth/callback", element: <OAuthCallback /> },
  {
    element: <RequireAuth />,
    children: [{ path: "/", element: <MainLayout /> }],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
