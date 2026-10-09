/** 主界面布局（M9-6；M10+ 账户管理 + 移除顶栏模型徽标）。
 *
 * 未登录由 RequireAuth 拦截，不渲染此布局；登录成功 navigate("/") 进入。
 * 账户管理：点击右上角头像 → 弹窗（选头像 / 改显示名 / 重置密码）。
 */

import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import {
  BookOpen,
  FileText,
  GitFork,
  KeyRound,
  LogOut,
  MessagesSquare,
  Scale,
  Settings,
  ShieldCheck,
  ScrollText,
  Menu,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  AUTH_LOGOUT_EVENT,
  clearAuth,
  getUser,
  updateStoredUser,
} from "@/api/client";
import { changePassword, updateProfile } from "@/api/auth";
import type { User } from "@/api/types";
import ApiKeySettings from "@/pages/ApiKeySettings";
import GraphPreview from "@/pages/GraphPreview";
import KnowledgeBase from "@/pages/KnowledgeBase";
import ModelConfig from "@/pages/ModelConfig";
import ReportView from "@/pages/ReportView";
import TaskList from "@/pages/TaskList";
import Workbench from "@/pages/Workbench";

type View = "tasks" | "graph" | "chat" | "report" | "models" | "knowledge" | "apikey";

interface NavItem {
  label: string;
  icon: typeof FileText;
  view: View;
  adminOnly?: boolean;
}

const navItems: NavItem[] = [
  { label: "任务列表", icon: FileText, view: "tasks" },
  // 新建审查与审查工作台原为同一视图（chat）的两条入口，导致双高亮 —— 合并为一项
  { label: "审查工作台", icon: MessagesSquare, view: "chat" },
  { label: "数据流图谱", icon: GitFork, view: "graph" },
  { label: "合规报告", icon: ScrollText, view: "report" },
  { label: "模型配置", icon: Settings, view: "models", adminOnly: true },
  { label: "API Key 设置", icon: KeyRound, view: "apikey" },
  { label: "知识库", icon: BookOpen, view: "knowledge" },
];

/** 头像候选 emoji（点击即保存为头像）。 */
const AVATAR_PRESETS = ["🦉", "⚖️", "🦁", "🦊", "🐼", "🦅", "🐙", "🛡️"];

/** 头像底色（按邮箱散列派生，同账号稳定；暖调传统色系：墨/朱/苔/赭/黛/栗）。 */
const AVATAR_COLORS = ["#3E3A34", "#9E3423", "#55663F", "#8C6A2F", "#3D5A66", "#6E4A3A"];

function avatarColor(email: string): string {
  let h = 0;
  for (let i = 0; i < email.length; i++) h = (h * 31 + email.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

/** 账户管理弹窗（M10+）：头像 / 显示名 / 改密码。 */
function AccountModal({
  user,
  onClose,
  onUpdated,
}: {
  user: User;
  onClose: () => void;
  onUpdated: (u: User) => void;
}) {
  const [displayName, setDisplayName] = useState(user.displayName ?? "");
  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  const [profileErr, setProfileErr] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwdMsg, setPwdMsg] = useState<string | null>(null);
  const [pwdErr, setPwdErr] = useState<string | null>(null);
  const [savingPwd, setSavingPwd] = useState(false);

  const saveProfile = async (payload: { displayName?: string; avatar?: string }) => {
    setProfileMsg(null);
    setProfileErr(null);
    setSavingProfile(true);
    try {
      const updated = await updateProfile(payload);
      onUpdated(updated);
      setProfileMsg("已保存");
    } catch (e) {
      setProfileErr(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSavingProfile(false);
    }
  };

  const submitPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdMsg(null);
    setPwdErr(null);
    if (!oldPassword || !newPassword) {
      setPwdErr("请填写旧密码与新密码");
      return;
    }
    if (newPassword.length < 6) {
      setPwdErr("新密码至少 6 位");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwdErr("两次输入的新密码不一致");
      return;
    }
    setSavingPwd(true);
    try {
      await changePassword(oldPassword, newPassword);
      setPwdMsg("密码已更新");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPwdErr(err instanceof Error ? err.message : "修改失败");
    } finally {
      setSavingPwd(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md border border-line-200 bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-ink-900">账户管理</h3>
          <button onClick={onClose} className="text-ink-400 hover:text-ink-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 用户信息 */}
        <div className="mb-5 flex items-center gap-3 rounded-xl bg-secondary p-3">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-xl text-paper shadow"
            style={{ backgroundColor: avatarColor(user.email) }}
          >
            {user.avatar ?? "👤"}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink-900">
              {user.displayName || user.email.split("@")[0]}
            </p>
            <p className="truncate text-xs text-ink-600">{user.email}</p>
          </div>
        </div>

        {/* 头像 */}
        <div className="mb-5">
          <p className="mb-2 text-xs font-medium text-ink-600">头像（点击即保存）</p>
          <div className="flex flex-wrap gap-2">
            {AVATAR_PRESETS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                disabled={savingProfile}
                onClick={() => saveProfile({ avatar: emoji })}
                className={`flex h-10 w-10 items-center justify-center rounded-full border text-xl transition-all ${
                  user.avatar === emoji
                    ? "border-brand-500 bg-brand-50 shadow-sm"
                    : "border-line-200 hover:border-brand-300 hover:bg-secondary"
                }`}
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>

        {/* 改名 */}
        <form
          className="mb-5"
          onSubmit={(e) => {
            e.preventDefault();
            saveProfile({ displayName: displayName.trim() });
          }}
        >
          <label className="mb-2 block text-xs font-medium text-ink-600">显示名</label>
          <div className="flex gap-2">
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="如：小法"
              className="h-9 flex-1 rounded-md border border-line-200 bg-card px-3 text-sm focus:border-brand-600 focus:outline-none"
            />
            <Button type="submit" size="sm" disabled={savingProfile}>
              {savingProfile ? "保存中…" : "保存"}
            </Button>
          </div>
          {profileMsg && <p className="mt-2 text-xs text-green-600">{profileMsg}</p>}
          {profileErr && <p className="mt-2 text-xs text-red-600">{profileErr}</p>}
        </form>

        {/* 改密码 */}
        <form onSubmit={submitPassword} className="border-t border-line-100 pt-4">
          <p className="mb-2 text-xs font-medium text-ink-600">重置密码</p>
          <div className="space-y-2">
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="当前密码"
              className="h-9 w-full rounded-md border border-line-200 bg-card px-3 text-sm focus:border-brand-600 focus:outline-none"
            />
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="新密码（至少 6 位）"
              className="h-9 w-full rounded-md border border-line-200 bg-card px-3 text-sm focus:border-brand-600 focus:outline-none"
            />
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="确认新密码"
              className="h-9 w-full rounded-md border border-line-200 bg-card px-3 text-sm focus:border-brand-600 focus:outline-none"
            />
          </div>
          {pwdMsg && <p className="mt-2 text-xs text-green-600">{pwdMsg}</p>}
          {pwdErr && <p className="mt-2 text-xs text-red-600">{pwdErr}</p>}
          <Button type="submit" size="sm" disabled={savingPwd} className="mt-3 w-full">
            {savingPwd ? "提交中…" : "确认修改密码"}
          </Button>
        </form>
      </div>
    </div>
  );
}

export function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  // 深链支持（App.tsx /tasks/:taskId、/reports/:taskId）：按路径派生初始视图与报告任务 ID
  const params = useParams<{ taskId?: string }>();
  const [user, setUser] = useState<User | null>(() => getUser<User>());
  const [view, setView] = useState<View>(() =>
    location.pathname === "/tasks/new"
      ? "chat"
      : location.pathname.startsWith("/reports")
        ? "report"
        : location.pathname.startsWith("/tasks")
          ? "tasks"
          : "graph",
  );
  const [reportTaskId, setReportTaskId] = useState(params.taskId ?? "");
  const [reportLoaded, setReportLoaded] = useState(Boolean(params.taskId));
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  /** 深链 /tasks/:taskId 的详情任务（传给工作台自动连 SSE）。 */
  const [detailTaskId, setDetailTaskId] = useState<string | null>(null);

  // 深链 / SPA 内跳转时视图跟随 URL（/tasks/new→工作台、/reports/:id→报告、/tasks/:id→工作台详情）
  useEffect(() => {
    const reportMatch = location.pathname.match(/^\/reports\/([^/]+)/);
    const taskMatch = location.pathname.match(/^\/tasks\/(?!new$)([^/]+)/);
    if (reportMatch) {
      setView("report");
      setReportTaskId(reportMatch[1]);
      setReportLoaded(true);
    } else if (taskMatch) {
      setView("chat");
      setDetailTaskId(taskMatch[1]);
    } else if (location.pathname === "/tasks/new") {
      setView("chat");
    } else if (location.pathname === "/tasks") {
      setView("tasks");
    }
    // 其余路径（/）不强制切换，保留用户当前视图
  }, [location.pathname]);

  // 监听全局登出事件（client.ts 401 触发）→ 跳登录页
  useEffect(() => {
    const onLogout = () => {
      setUser(null);
      navigate("/login", { replace: true });
    };
    window.addEventListener(AUTH_LOGOUT_EVENT, onLogout);
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
  }, [navigate]);

  const handleLogout = () => {
    clearAuth();
    navigate("/login", { replace: true });
  };

  const handleAccountUpdated = (updated: User) => {
    setUser(updated);
    updateStoredUser(updated);
  };

  const visibleNav = navItems.filter((item) => !item.adminOnly || user?.role === "admin");
  const isAdmin = user?.role === "admin";

  return (
    <div className="flex h-screen bg-paper text-ink-900">
      {/* 移动端菜单按钮 */}
      <div className="fixed top-4 left-4 z-50 md:hidden">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="border-line-200 bg-card shadow-sm"
        >
          {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </Button>
      </div>

      {/* 侧边栏 */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-line-200 bg-card shadow-sm transition-transform duration-300 ease-in-out md:static md:translate-x-0 ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-3 p-5 border-b border-line-100">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-ink-900">
            <Scale className="h-5 w-5 text-paper" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-ink-900">LegalEye</h2>
            <p className="text-xs text-ink-600">法眼</p>
          </div>
        </div>

        <nav className="flex-1 p-3">
          <div className="space-y-1">
            {visibleNav.map((item) => (
              <button
                key={item.label}
                type="button"
                onClick={() => {
                  setView(item.view);
                  setMobileMenuOpen(false);
                }}
                className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 ${
                  view === item.view
                    ? "bg-ink-900 text-paper"
                    : "text-ink-900 hover:bg-secondary"
                }`}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </button>
            ))}
          </div>
        </nav>

        <div className="p-4 border-t border-line-100">
          <div className="flex items-center gap-2 rounded-lg bg-secondary p-3">
            <ShieldCheck className="h-5 w-5 text-green-500" />
            <div className="text-xs text-ink-600">
              数据不出境<br />
              <span className="font-medium">默认百炼</span>
            </div>
          </div>
        </div>
      </aside>

      {/* 遮罩层 - 移动端 */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        ></div>
      )}

      {/* 主区 */}
      <div className="flex flex-1 flex-col md:ml-0">
        {/* 顶栏 */}
        <header className="flex h-16 items-center justify-between border-b border-line-200 bg-card px-4 shadow-sm md:px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="md:hidden text-ink-600 hover:text-ink-900"
            >
              <Menu className="h-5 w-5" />
            </button>
            <span className="text-sm font-medium text-ink-900 hidden md:block">
              出海企业数据合规智能审查
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-sm text-ink-900 hidden md:block">
              {user?.displayName || user?.email.split("@")[0]}
              {isAdmin && (
                <span className="ml-2 rounded bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700">
                  admin
                </span>
              )}
            </span>
            {/* 头像按钮 → 账户管理 */}
            <button
              type="button"
              onClick={() => setAccountOpen(true)}
              title="账户管理"
              className="flex h-9 w-9 items-center justify-center rounded-full text-base text-paper shadow transition-transform hover:scale-105"
              style={{ backgroundColor: avatarColor(user?.email ?? "") }}
            >
              {user?.avatar ?? "👤"}
            </button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleLogout}
              className="hidden md:flex items-center gap-1 text-sm"
            >
              <LogOut className="h-4 w-4" />
              退出
            </Button>
          </div>
        </header>

        {/* 内容区 */}
        <main className="flex-1 overflow-auto p-4 md:p-6">
          {view === "graph" && <GraphPreview />}
          {view === "chat" && (
            <Workbench
              key={detailTaskId ?? "blank"}
              initialTaskId={detailTaskId ?? undefined}
            />
          )}
          {view === "tasks" && <TaskList />}
          {view === "models" && user && isAdmin && <ModelConfig />}
          {view === "apikey" && <ApiKeySettings />}
          {view === "knowledge" && <KnowledgeBase />}
          {view === "report" &&
            (reportLoaded ? (
              <ReportView taskId={reportTaskId} onBack={() => setReportLoaded(false)} />
            ) : (
              <div className="flex flex-col items-center justify-center gap-4 py-12 text-center">
                <div className="border border-line-200 bg-secondary p-4">
                  <ScrollText className="h-8 w-8 text-brand-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-ink-900">查看合规报告</h3>
                  <p className="mt-1 text-sm text-ink-600">输入任务 ID 查看合规审查报告</p>
                </div>
                <div className="flex flex-col sm:flex-row gap-3 w-full max-w-md">
                  <input
                    value={reportTaskId}
                    onChange={(e) => setReportTaskId(e.target.value)}
                    placeholder="任务 ID"
                    className="flex-1 rounded-lg border border-line-200 bg-card px-4 py-3 text-sm focus:border-brand-600 focus:outline-none"
                  />
                  <Button
                    onClick={() => reportTaskId.trim() && setReportLoaded(true)}
                    disabled={!reportTaskId.trim()}
                    className="bg-primary hover:bg-brand-700"
                  >
                    查看报告
                  </Button>
                </div>
              </div>
            ))}
        </main>
      </div>

      {/* 账户管理弹窗 */}
      {accountOpen && user && (
        <AccountModal
          user={user}
          onClose={() => setAccountOpen(false)}
          onUpdated={handleAccountUpdated}
        />
      )}
    </div>
  );
}
