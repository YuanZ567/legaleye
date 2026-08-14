import { useEffect, useState } from "react";
import {
  BookOpen,
  FileText,
  GitFork,
  LogOut,
  MessagesSquare,
  PlusCircle,
  Settings,
  ShieldCheck,
  ScrollText,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { AUTH_LOGOUT_EVENT, clearAuth, getUser } from "@/api/client";
import { fetchModels } from "@/api/models";
import type { ModelConfig as ModelConfigType, User } from "@/api/types";
import GraphPreview from "@/pages/GraphPreview";
import KnowledgeBase from "@/pages/KnowledgeBase";
import Login from "@/pages/Login";
import ModelConfig from "@/pages/ModelConfig";
import ReportView from "@/pages/ReportView";
import TaskList from "@/pages/TaskList";
import Workbench from "@/pages/Workbench";

type View = "tasks" | "graph" | "chat" | "report" | "login" | "models" | "knowledge";

interface NavItem {
  label: string;
  icon: typeof FileText;
  view: View;
  adminOnly?: boolean;
}

const navItems: NavItem[] = [
  { label: "任务列表", icon: FileText, view: "tasks" },
  { label: "新建审查", icon: PlusCircle, view: "chat" },
  { label: "审查工作台", icon: MessagesSquare, view: "chat" },
  { label: "数据流图谱", icon: GitFork, view: "graph" },
  { label: "合规报告", icon: ScrollText, view: "report" },
  { label: "模型配置", icon: Settings, view: "models", adminOnly: true },
  { label: "知识库", icon: BookOpen, view: "knowledge" },
];

/** M9-5 应用壳：鉴权路由 + 侧边栏（admin 菜单过滤）+ 顶栏（模型状态从 API 读）。 */
export default function App() {
  const [user, setUser] = useState<User | null>(() => getUser<User>());
  const [view, setView] = useState<View>(() => (getUser() ? "graph" : "login"));
  const [reportTaskId, setReportTaskId] = useState("");
  const [reportLoaded, setReportLoaded] = useState(false);
  const [activeModel, setActiveModel] = useState<ModelConfigType | null>(null);

  // 监听全局登出事件（client.ts 401 触发）
  useEffect(() => {
    const onLogout = () => {
      setUser(null);
      setView("login");
    };
    window.addEventListener(AUTH_LOGOUT_EVENT, onLogout);
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
  }, []);

  // 已登录时从 API 拉取当前激活模型（顶部状态栏，禁硬编码）
  useEffect(() => {
    if (!user) {
      setActiveModel(null);
      return;
    }
    fetchModels()
      .then((models) => setActiveModel(models.find((m) => m.isActive) ?? null))
      .catch(() => setActiveModel(null)); // 非 admin 403 等 → 降级默认
  }, [user]);

  const handleLoggedIn = (u: User) => {
    setUser(u);
    setView("graph");
  };

  const handleLogout = () => {
    clearAuth();
    setUser(null);
    setView("login");
  };

  const visibleNav = navItems.filter((item) => !item.adminOnly || user?.role === "admin");
  const isAdmin = user?.role === "admin";

  return (
    <div className="flex h-screen bg-paper text-ink-900">
      {/* 侧边栏 */}
      <aside className="flex w-56 shrink-0 flex-col border-r border-line-200 bg-surface px-3 py-4">
        <div className="mb-6 flex items-center gap-2 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
            L
          </div>
          <span className="text-sm font-semibold">LegalEye 法眼</span>
        </div>
        <nav className="flex flex-col gap-1">
          {visibleNav.map((item) => (
            <button
              key={item.label}
              type="button"
              onClick={() => setView(item.view)}
              className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm text-left ${
                view === item.view
                  ? "bg-brand-50 font-medium text-brand-700"
                  : "text-ink-600 hover:bg-muted"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="mt-auto flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-xs text-ink-400">
          <ShieldCheck className="h-4 w-4 text-risk-ok" />
          数据不出境 · 默认百炼
        </div>
      </aside>

      {/* 主区 */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-line-200 bg-surface px-6">
          <span className="text-sm text-ink-600">出海企业数据合规智能审查</span>
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-brand-50 px-3 py-1 font-mono text-xs text-brand-700">
              {activeModel ? `${activeModel.displayName} · ${activeModel.model}` : "默认百炼"}
            </span>
            {user ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-ink-600">
                  {user.email}
                  {isAdmin && (
                    <span className="ml-1 rounded bg-brand-50 px-1.5 py-0.5 text-xs text-brand-700">
                      admin
                    </span>
                  )}
                </span>
                <Button size="sm" variant="outline" onClick={handleLogout}>
                  <LogOut className="h-3 w-3" />
                  退出
                </Button>
              </div>
            ) : (
              <Button size="sm" onClick={() => setView("login")}>
                登录
              </Button>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          {view === "login" && <Login onLoggedIn={handleLoggedIn} />}
          {view === "graph" && user && <GraphPreview />}
          {view === "chat" && user && <Workbench />}
          {view === "tasks" && user && <TaskList />}
          {view === "models" && user && isAdmin && <ModelConfig />}
          {view === "knowledge" && user && <KnowledgeBase />}
          {view === "report" &&
            user &&
            (reportLoaded ? (
              <ReportView taskId={reportTaskId} onBack={() => setReportLoaded(false)} />
            ) : (
              <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
                <ScrollText className="h-8 w-8 text-ink-400" />
                <p className="text-sm text-ink-600">输入任务 ID 查看合规报告</p>
                <div className="flex gap-2">
                  <input
                    value={reportTaskId}
                    onChange={(e) => setReportTaskId(e.target.value)}
                    placeholder="任务 ID"
                    className="h-9 w-72 rounded-md border border-line-200 bg-surface px-3 text-sm focus:border-brand-600 focus:outline-none"
                  />
                  <Button
                    onClick={() => reportTaskId.trim() && setReportLoaded(true)}
                    disabled={!reportTaskId.trim()}
                  >
                    查看报告
                  </Button>
                </div>
              </div>
            ))}
        </main>
      </div>
    </div>
  );
}
