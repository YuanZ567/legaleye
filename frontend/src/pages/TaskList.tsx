/** 任务列表页（M8-4）：卡片式任务列表 + 状态筛选 + 新建入口。
 *
 * 对齐 DESIGN 14.2 token：queued 灰 / running 蓝 #1570EF / done 绿 #12B76A / failed 红 #D92D20。
 */

import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PlusCircle, Search, Calendar, Clock, FileText, XCircle, RefreshCw } from "lucide-react";

import { deleteTask, fetchTasks } from "@/api/tasks";
import { getUser } from "@/api/client";
import type { ReviewTask, User } from "@/api/types";
import { Button } from "@/components/ui/button";

const STATUS_COLOR: Record<string, string> = {
  queued: "#8A93A6",
  running: "#1570EF",
  done: "#12B76A",
  failed: "#D92D20",
  degraded: "#DC6803",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ backgroundColor: `${STATUS_COLOR[status] ?? "#8A93A6"}1A`, color: STATUS_COLOR[status] ?? "#8A93A6" }}
    >
      {status}
    </span>
  );
}

const STATUS_OPTIONS = ["all", "queued", "running", "done", "failed"];

export default function TaskList() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [deletingTaskId, setDeletingTaskId] = useState<string | null>(null);

  useEffect(() => {
    const user = getUser<User>();
    setIsAdmin(user?.role === "admin");
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTasks(filter);
      setTasks(data);
    } catch {
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const filteredTasks = tasks.filter(task => {
    const matchesStatus = filter === "all" || task.status === filter;
    // 支持任务 ID / 文档 ID / 文件名搜索
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      task.id.toLowerCase().includes(q) ||
      (task.documentId ?? "").toLowerCase().includes(q) ||
      (task.documentFilename ?? "").toLowerCase().includes(q);
    return matchesStatus && matchesSearch;
  });

  const handleDelete = async (task: ReviewTask) => {
    if (
      !window.confirm(
        `确定删除任务 ${task.id.slice(0, 8)}？关联的审查结果和报告将一并删除。`,
      )
    ) {
      return;
    }
    setDeletingTaskId(task.id);
    try {
      await deleteTask(task.id);
      setTasks((prev) => prev.filter((t) => t.id !== task.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    } finally {
      setDeletingTaskId(null);
    }
  };

  const handleRefresh = () => {
    load();
  };

  return (
    <div className="space-y-6">
      {/* 顶部工具栏 */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">任务列表</h1>
          <p className="mt-1 text-sm text-ink-600">查看和管理合规审查任务</p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            刷新
          </Button>
          <Button
            onClick={() => navigate("/tasks/new")}
            className="flex items-center gap-2 bg-primary hover:bg-brand-700"
          >
            <PlusCircle className="h-4 w-4" />
            新建审查
          </Button>
        </div>
      </div>

      {/* 筛选器和搜索 */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
            <input
              type="text"
              placeholder="搜索任务 ID / 文档 ID / 文件名..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-line-200 bg-card pl-10 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 shadow-sm"
            />
          </div>

          <div className="flex gap-2">
            {STATUS_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-200 ${
                  filter === s
                    ? "bg-ink-900 text-paper"
                    : "bg-secondary text-ink-900 hover:bg-line-200"
                }`}
              >
                {s === "all" ? "全部" :
                 s === "queued" ? "排队中" :
                 s === "running" ? "运行中" :
                 s === "done" ? "已完成" : "失败"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 任务卡片视图 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading && tasks.length === 0 ? (
          <div className="col-span-full flex flex-col items-center justify-center gap-3 py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent"></div>
            <span className="text-sm text-ink-600">加载任务中...</span>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="col-span-full flex flex-col items-center justify-center gap-4 py-12 text-center">
            <div className="rounded-full bg-secondary p-4">
              <FileText className="h-8 w-8 text-ink-600" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-ink-900">暂无任务</h3>
              <p className="mt-1 text-sm text-ink-600">创建一个新任务开始审查</p>
            </div>
            <Button
              onClick={() => navigate("/tasks/new")}
              className="mt-2 bg-primary hover:bg-brand-700"
            >
              创建第一个任务
            </Button>
          </div>
        ) : (
          filteredTasks.map((task) => (
            <div key={task.id} className="rounded-xl border border-line-200 bg-card p-5 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-line-200 bg-secondary">
                    <FileText className="h-6 w-6 text-brand-600" />
                  </div>
                  <div>
                    <div className="max-w-[220px] truncate text-sm font-semibold text-ink-900" title={task.documentFilename ?? task.id}>
                      {task.documentFilename ?? task.id}
                    </div>
                    <div className="text-xs text-ink-600 mt-1">
                      <span className="font-mono">{task.id.slice(0, 8)}</span>
                      <span className="mx-1.5">·</span>发现数: {task.findingCount}
                    </div>
                  </div>
                </div>
                <StatusBadge status={task.status} />
              </div>

              <div className="mt-4 space-y-2">
                <div className="flex items-center gap-2 text-sm text-ink-600">
                  <Calendar className="h-4 w-4" />
                  <span>{new Date(task.createdAt).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-ink-600">
                  <Clock className="h-4 w-4" />
                  <span>{task.progress}% 完成</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-ink-600">
                  <FileText className="h-4 w-4" />
                  <span>{task.documentId ? 1 : 0} 个文档</span>
                </div>
              </div>

              <div className="mt-4 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/reports/${task.id}`)}
                  className="flex-1"
                >
                  查看报告
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/tasks/${task.id}`)}
                  className="flex-1"
                >
                  详情
                </Button>
                {isAdmin && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(task)}
                    disabled={deletingTaskId === task.id}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    {deletingTaskId === task.id ? "删除中..." : "删除"}
                  </Button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-red-600" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        </div>
      )}
    </div>
  );
}
