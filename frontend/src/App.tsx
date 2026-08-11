import { BookOpen, FileText, PlusCircle, Settings, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";

const navItems = [
  { label: "任务列表", icon: FileText, active: true },
  { label: "新建审查", icon: PlusCircle },
  { label: "模型配置", icon: Settings },
  { label: "知识库", icon: BookOpen },
];

/** M0 应用壳：侧边栏 + 顶栏 + 内容区占位（DESIGN.md 7.1 布局）。 */
export default function App() {
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
            <a
              key={item.label}
              href="#"
              className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm ${
                item.active
                  ? "bg-brand-50 font-medium text-brand-700"
                  : "text-ink-600 hover:bg-muted"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </a>
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
        <main className="flex-1 p-6">
          <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-line-200">
            <p className="text-sm text-ink-400">M0 应用壳占位 — M1 起填充任务列表与审查工作台</p>
          </div>
        </main>
      </div>
    </div>
  );
}
