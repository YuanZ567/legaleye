/** 登录/注册页（M9-6）：独立全屏页（无导航/侧边栏，路由 /login）。
 *
 * - 登录/注册双模式 + 邮箱密码；
 * - 第三方登录：GitHub（全链路）+ QQ（接口就绪，凭据留空标注"暂未开通"）；
 * - 成功后 saveAuth → navigate("/") 进入主界面。
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GitBranch } from "lucide-react";

import { login as apiLogin, register as apiRegister } from "@/api/auth";
import { saveAuth } from "@/api/client";
import { Button } from "@/components/ui/button";

type Mode = "login" | "register";

/** 后端 OAuth authorize 基址（配 api_base_url，禁硬编码 host）。 */
const OAUTH_BASE = "http://localhost:8000";

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email.trim() || !password) {
      setError("请填写邮箱与密码");
      return;
    }
    setSubmitting(true);
    try {
      const auth =
        mode === "login"
          ? await apiLogin(email.trim(), password)
          : await apiRegister(email.trim(), password);
      saveAuth(auth.token, auth.user);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setSubmitting(false);
    }
  };

  const switchMode = (m: Mode) => {
    setMode(m);
    setError(null);
  };

  /** 发起第三方登录（GitHub 全链路；QQ 接口就绪但凭据留空 → 后端 503）。 */
  const oauthLogin = (provider: "github" | "qq") => {
    window.location.href = `${OAUTH_BASE}/auth/oauth/${provider}/authorize`;
  };

  return (
    <div
      className="flex min-h-screen items-center justify-center bg-paper px-4"
      style={{
        backgroundImage:
          "linear-gradient(rgba(238,241,253,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(238,241,253,0.5) 1px, transparent 1px)",
        backgroundSize: "24px 24px",
      }}
    >
      <div className="w-full max-w-[400px] rounded-lg border border-line-200 bg-surface p-8 shadow-sm">
        {/* 品牌 */}
        <div className="mb-6 flex flex-col items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 text-base font-semibold text-white">
            L
          </div>
          <h1 className="text-lg font-semibold text-ink-900">LegalEye 法眼</h1>
          <p className="text-xs text-ink-400">出海企业数据合规智能审查</p>
        </div>

        {/* 第三方登录 */}
        <div className="mb-5 space-y-2">
          <button
            type="button"
            onClick={() => oauthLogin("github")}
            className="flex w-full items-center justify-center gap-2 rounded-md border border-line-200 bg-surface px-3 py-2 text-sm font-medium text-ink-700 transition-colors hover:bg-muted"
          >
            <GitBranch className="h-4 w-4" />
            使用 GitHub 登录
          </button>
          <button
            type="button"
            onClick={() => oauthLogin("qq")}
            className="flex w-full items-center justify-center gap-2 rounded-md border border-line-200 bg-surface px-3 py-2 text-sm font-medium text-ink-400 transition-colors hover:bg-muted"
          >
            QQ 登录
            <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-ink-400">暂未开通</span>
          </button>
          <div className="flex items-center gap-3 py-1 text-xs text-ink-400">
            <span className="h-px flex-1 bg-line-200" />
            或使用邮箱
            <span className="h-px flex-1 bg-line-200" />
          </div>
        </div>

        {/* 模式切换 */}
        <div className="mb-5 flex rounded-md bg-muted p-0.5">
          {(["login", "register"] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => switchMode(m)}
              className={`flex-1 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                mode === m
                  ? "bg-surface text-brand-700 shadow-xs"
                  : "text-ink-500 hover:text-ink-700"
              }`}
            >
              {m === "login" ? "登录" : "注册"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="h-9 w-full rounded-md border border-line-200 bg-surface px-3 text-sm focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/30"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === "login" ? "请输入密码" : "至少 6 位"}
              className="h-9 w-full rounded-md border border-line-200 bg-surface px-3 text-sm focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/30"
            />
          </div>

          {error && (
            <p className="rounded-md border border-risk-high/30 bg-[#FEF3F2] px-3 py-2 text-xs text-risk-highText">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "处理中…" : mode === "login" ? "登录" : "注册并登录"}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-ink-400">
          {mode === "login" ? "首次使用？" : "已有账号？"}
          <button
            type="button"
            onClick={() => switchMode(mode === "login" ? "register" : "login")}
            className="ml-1 font-medium text-brand-600 hover:text-brand-700"
          >
            {mode === "login" ? "注册新账号" : "去登录"}
          </button>
        </p>
      </div>
    </div>
  );
}
