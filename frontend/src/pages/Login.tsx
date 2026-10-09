/** 登录/注册页（M9-6；M10+ 忘记密码 + 公文卷宗风改版）。
 *
 * - 三模式：登录 / 注册 / 忘记密码（按注册邮箱直接重置，本项目无邮件服务）；
 * - 第三方登录：GitHub（全链路）；
 * - 视觉：暖纸底 + 发丝线双框 + 宋体标题 + 朱砂印记；无渐变/毛玻璃。
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GitBranch, Eye, EyeOff, Scale } from "lucide-react";

import {
  login as apiLogin,
  register as apiRegister,
  resetPassword as apiResetPassword,
} from "@/api/auth";
import { saveAuth } from "@/api/client";
import { Button } from "@/components/ui/button";

type Mode = "login" | "register" | "forgot";

/** 后端 OAuth authorize 基址（配 api_base_url，禁硬编码 host）。 */
const OAUTH_BASE = "http://localhost:8000";

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    if (mode === "forgot") {
      if (!email.trim() || !password) {
        setError("请填写注册邮箱与新密码");
        return;
      }
      if (password !== confirmPassword) {
        setError("两次输入的新密码不一致");
        return;
      }
      setSubmitting(true);
      try {
        await apiResetPassword(email.trim(), password);
        setNotice("密码已重置，请使用新密码登录");
        setMode("login");
        setPassword("");
        setConfirmPassword("");
      } catch (err) {
        setError(err instanceof Error ? err.message : "重置失败");
      } finally {
        setSubmitting(false);
      }
      return;
    }
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
    setNotice(null);
    setPassword("");
    setConfirmPassword("");
  };

  /** 发起第三方登录（GitHub 全链路）。 */
  const oauthLogin = () => {
    window.location.href = `${OAUTH_BASE}/auth/oauth/github/authorize`;
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4">
      {/* 公文双线框卡片：外层发丝线 + 内层细线，替代玻璃拟态 */}
      <div className="relative w-full max-w-[420px] border border-line-200 bg-card shadow-lg">
        <div className="m-1.5 border border-line-100 p-8">
          {/* 品牌：天平图标（法律符号）+ 宋体标题 */}
          <div className="mb-8 flex flex-col items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-xl border-2 border-ink-900 bg-card">
              <Scale className="h-8 w-8 text-brand-600" />
            </div>
            <div className="text-center">
              <h1 className="font-display text-2xl font-bold tracking-wide text-ink-900">
                LegalEye 法眼
              </h1>
              <p className="mt-2 text-sm text-ink-600">出海企业数据合规智能审查</p>
            </div>
          </div>

          {/* 第三方登录（仅 GitHub；忘记密码模式下隐藏） */}
          {mode !== "forgot" && (
            <div className="mb-6 space-y-3">
              <button
                type="button"
                onClick={oauthLogin}
                className="flex w-full items-center justify-center gap-3 border border-line-200 bg-card px-4 py-3 text-sm font-medium text-ink-900 transition-colors duration-200 hover:bg-secondary"
              >
                <GitBranch className="h-5 w-5" />
                使用 GitHub 登录
              </button>
              <div className="relative flex items-center py-2">
                <div className="flex-1 border-t border-line-200"></div>
                <span className="mx-4 text-xs text-ink-400">或使用邮箱</span>
                <div className="flex-1 border-t border-line-200"></div>
              </div>
            </div>
          )}

          {/* 模式切换（登录/注册；忘记密码为独立子页） */}
          {mode !== "forgot" ? (
            <div className="mb-6 flex border border-line-200 p-1">
              {(["login", "register"] as Mode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => switchMode(m)}
                  className={`flex-1 px-4 py-2 text-sm font-medium transition-colors duration-200 ${
                    mode === m
                      ? "bg-ink-900 font-medium text-paper"
                      : "text-ink-600 hover:text-ink-900"
                  }`}
                >
                  {m === "login" ? "登录" : "注册"}
                </button>
              ))}
            </div>
          ) : (
            <div className="mb-6">
              <h2 className="text-center font-display text-base font-bold text-ink-900">
                重置密码
              </h2>
              <p className="mt-1 text-center text-xs text-ink-400">
                输入注册邮箱与新密码，验证通过后直接重置
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-medium text-ink-600">
                {mode === "forgot" ? "注册邮箱" : "邮箱地址"}
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full border border-line-200 bg-card px-4 py-3 text-sm transition-colors duration-200 focus:border-brand-600 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-ink-600">
                {mode === "forgot" ? "新密码" : "密码"}
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={
                    mode === "register" || mode === "forgot" ? "至少 6 位" : "请输入密码"
                  }
                  className="w-full border border-line-200 bg-card px-4 py-3 pr-12 text-sm transition-colors duration-200 focus:border-brand-600 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-400 hover:text-ink-600"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>
            {mode === "forgot" && (
              <div>
                <label className="mb-2 block text-sm font-medium text-ink-600">确认新密码</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="再次输入新密码"
                  className="w-full border border-line-200 bg-card px-4 py-3 text-sm transition-colors duration-200 focus:border-brand-600 focus:outline-none"
                />
              </div>
            )}

            {error && (
              <div className="border border-risk-high/30 bg-[#FBF1EE] px-4 py-3 text-sm text-risk-highText">
                {error}
              </div>
            )}
            {notice && (
              <div className="border border-line-200 bg-secondary px-4 py-3 text-sm text-ink-900">
                {notice}
              </div>
            )}

            <Button
              type="submit"
              className="w-full bg-primary py-3 font-medium text-primary-foreground transition-colors duration-200 hover:bg-brand-700"
              disabled={submitting}
            >
              {submitting ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-primary-foreground" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  处理中...
                </span>
              ) : mode === "login" ? "登录" : mode === "register" ? "注册并登录" : "重置密码"}
            </Button>
          </form>

          {/* 忘记密码 / 返回登录 */}
          <div className="mt-4 text-center">
            {mode === "forgot" ? (
              <button
                type="button"
                onClick={() => switchMode("login")}
                className="text-sm font-medium text-brand-600 hover:text-brand-700 transition-colors duration-200"
              >
                ← 返回登录
              </button>
            ) : (
              <div className="flex items-center justify-center gap-4 text-sm">
                <span className="text-ink-600">
                  {mode === "login" ? "首次使用？" : "已有账号？"}
                  <button
                    type="button"
                    onClick={() => switchMode(mode === "login" ? "register" : "login")}
                    className="ml-1 font-medium text-brand-600 hover:text-brand-700 transition-colors duration-200"
                  >
                    {mode === "login" ? "注册新账号" : "去登录"}
                  </button>
                </span>
                {mode === "login" && (
                  <button
                    type="button"
                    onClick={() => switchMode("forgot")}
                    className="text-ink-400 hover:text-brand-600 transition-colors duration-200"
                  >
                    忘记密码？
                  </button>
                )}
              </div>
            )}
          </div>

          {/* 安全提示：发丝线脚注，替代彩色提示块 */}
          <div className="mt-8 border-t border-line-200 pt-4 text-center">
            <p className="text-xs text-ink-400">
              数据安全承诺：我们承诺保护您的隐私，所有数据均采用加密传输和存储
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
