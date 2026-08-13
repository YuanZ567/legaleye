import { useState } from "react";
import { BookOpen, FileText, GitFork, MessagesSquare, PlusCircle, Settings, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import GraphPreview from "@/pages/GraphPreview";
import Workbench from "@/pages/Workbench";

type View = "tasks" | "graph" | "chat";

const navItems: { label: string; icon: typeof FileText; view: View }[] = [
  { label: "任务列表", icon: FileText, view: "tasks" },
  { label: "新建审查", icon: PlusCircle, view: "chat" },
  { label: "审查工作台", icon: MessagesSquare, view: "chat" },
  { label: "数据流图谱", icon: GitFork, view: "graph" },
  { label: "模型配置", icon: Settings, view: "tasks" },
  { label: "知识库", icon: BookOpen, view: "tasks" },
];

/** M0 应用壳：侧边栏 + 顶栏 + 内容区（M3-5 接入数据流图谱 React Flow）。 */
export default function App() {
  const [view, setView] = useState<View>("graph");
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
          {navItems.map((item) => (
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
              百炼 · qwen-plus
            </span>
            <Button size="sm">登录</Button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          {view === "graph" && <GraphPreview />}
          {view === "chat" && <Workbench />}
          {view === "tasks" && (
            <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-line-200">
              <p className="text-sm text-ink-400">该视图占位 — 任务列表（M8）</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
