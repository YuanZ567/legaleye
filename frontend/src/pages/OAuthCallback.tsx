/** OAuth 回调处理页（M9-6，路由 /oauth/callback）。
 *
 * 后端完成第三方授权后 302 跳转至此并携带 token；本页：
 * 1. 读取 ?token=；
 * 2. 存入 localStorage（供 /auth/me 携带 Bearer）；
 * 3. 调 GET /auth/me 拉取用户 → saveAuth(token, user)；
 * 4. 跳主界面 /。
 */

import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { fetchMe } from "@/api/auth";
import { saveAuth } from "@/api/client";

export default function OAuthCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;
    const token = params.get("token");
    if (!token) {
      setError("回调缺少 token");
      return;
    }
    (async () => {
      try {
        // 先存 token（/auth/me 依赖它鉴权），再拉用户
        localStorage.setItem("legaleye_token", token);
        const user = await fetchMe();
        saveAuth(token, user);
        navigate("/", { replace: true });
      } catch (e) {
        localStorage.removeItem("legaleye_token");
        setError(e instanceof Error ? e.message : "OAuth 登录失败");
      }
    })();
  }, [params, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper">
      <div className="text-center text-sm text-ink-500">
        {error ? <p className="text-risk-highText">{error}</p> : <p>第三方登录验证中…</p>}
        {error && (
          <button
            type="button"
            onClick={() => navigate("/login")}
            className="mt-4 text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            返回登录
          </button>
        )}
      </div>
    </div>
  );
}
