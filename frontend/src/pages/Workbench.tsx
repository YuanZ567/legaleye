/** 审查工作台（M7-5；M10+ 内置新建审查流程）。
 *
 * 新建审查面板：选择本地文档（可多选）+ 文档类型 → 上传 → 创建审查任务，
 * 自动用返回的 taskId 连接 SSE 实时流、首个文档 ID 渲染数据流图谱。
 * 四栏同页实时联动（聊天 / 编排画布 / 数据流图谱 / 仪表盘）。
 */

import { useEffect, useRef, useState } from "react";

import ChatPanel from "@/components/ChatPanel";
import Dashboard from "@/components/Dashboard";
import OrchestrationCanvas from "@/components/OrchestrationCanvas";
import { useSSE } from "@/hooks/useSSE";
import { uploadDocument } from "@/api/documents";
import type { DocumentInfo } from "@/api/documents";
import { createTask, fetchTask } from "@/api/tasks";
import { fetchReport } from "@/api/reports";
import type { ReviewTask } from "@/api/types";
import GraphPreview from "@/pages/GraphPreview";
import { Button } from "@/components/ui/button";

const DOC_TYPES = [
  { value: "privacyPolicy", label: "隐私政策" },
  { value: "userAgreement", label: "用户协议" },
  { value: "dpa", label: "DPA 数据处理协议" },
  { value: "scc", label: "SCC 标准合同" },
];

export default function Workbench({ initialTaskId }: { initialTaskId?: string }) {
  // 详情深链 /tasks/:taskId 会带 initialTaskId 进来，自动连 SSE
  const [taskId, setTaskId] = useState(initialTaskId ?? "");
  const { status, activeNodes, tokenUsage, connected } = useSSE(taskId || null);
  const [graphDocId, setGraphDocId] = useState("");
  // 详情任务已完成 → 编排画布直接标全绿（SSE 无新事件也能看到终态）
  const [taskDone, setTaskDone] = useState(false);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [taskInfo, setTaskInfo] = useState<ReviewTask | null>(null);
  const [risk, setRisk] = useState<{ high: number; medium: number; low: number } | null>(null);

  // 详情深链：拉任务详情，自动填图谱文档 ID + 完成态 + 仪表盘真实数据
  useEffect(() => {
    if (!initialTaskId) return;
    fetchTask(initialTaskId)
      .then((t) => {
        setTaskInfo(t);
        if (t.documentId) setGraphDocId(t.documentId);
        if (t.status === "done") setTaskDone(true);
        if (t.error) setTaskError(t.error);
      })
      .catch(() => {
        // 详情拉取失败不阻塞 SSE，静默降级
      });
    // 报告就绪后聚合风险分布（404 = 未生成，忽略）
    fetchReport(initialTaskId)
      .then((rep) => {
        setRisk({
          high: rep.findings.filter((f) => f.level === "high").length,
          medium: rep.findings.filter((f) => f.level === "medium").length,
          low: rep.findings.filter((f) => f.level === "low").length,
        });
      })
      .catch(() => {});
  }, [initialTaskId]);

  // 新建审查表单
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [docType, setDocType] = useState(DOC_TYPES[0].value);
  const [sensitiveMode, setSensitiveMode] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [uploadedDocs, setUploadedDocs] = useState<DocumentInfo[]>([]);

  const handleCreate = async () => {
    setCreateError(null);
    if (files.length === 0) {
      setCreateError("请先选择至少一个文档（.md / .txt 等）");
      return;
    }
    setCreating(true);
    try {
      // 1) 逐个上传文档
      const docs: DocumentInfo[] = [];
      for (const file of files) {
        docs.push(await uploadDocument(file, docType, sensitiveMode));
      }
      // 2) 创建审查任务
      const newTaskId = await createTask(docs.map((d) => d.id));
      // 3) 自动连接 SSE + 图谱
      setTaskId(newTaskId);
      setGraphDocId(docs[0].id);
      setUploadedDocs(docs);
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 新建审查面板 */}
      <div className="rounded-lg border border-line-200 bg-card p-4">
        <h3 className="mb-3 text-sm font-semibold text-ink-900">新建审查</h3>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
          <div className="flex-1">
            <label className="mb-1 block text-xs font-medium text-ink-600">
              合规文档（可多选；多文档将触发跨文档矛盾检测）
            </label>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".md,.txt,.markdown,.pdf,.docx"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
              className="block w-full text-sm text-ink-600 file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-2 file:text-sm file:font-medium file:text-ink-900 hover:file:bg-line-200"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600">文档类型</label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="h-9 w-44 rounded-md border border-line-200 bg-card px-2 text-sm focus:border-brand-600 focus:outline-none"
            >
              {DOC_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-ink-600">
            <input
              type="checkbox"
              checked={sensitiveMode}
              onChange={(e) => setSensitiveMode(e.target.checked)}
              className="h-4 w-4 accent-[#9E3423]"
            />
            敏感模式
          </label>
          <Button onClick={handleCreate} disabled={creating} className="bg-primary hover:bg-brand-700">
            {creating ? "上传并创建中…" : "创建审查任务"}
          </Button>
        </div>
        {createError && (
          <p className="mt-2 rounded-md border border-risk-high/30 bg-[#FBF1EE] px-3 py-2 text-xs text-risk-highText">
            {createError}
          </p>
        )}
        {uploadedDocs.length > 0 && taskId && (
          <p className="mt-2 text-xs text-ink-600">
            已创建任务{" "}
            <span className="font-mono text-brand-600">{taskId.slice(0, 8)}</span>
            {" "}（{uploadedDocs.map((d) => d.filename).join("、")}），下方四栏已实时联动。
          </p>
        )}
      </div>

      {/* 任务连接栏 */}
      <div className="flex items-center gap-3 rounded-lg border border-line-200 bg-card px-4 py-3">
        <span
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: connected ? "#12B76A" : "#D92D20" }}
        />
        <span className="text-sm font-medium text-ink-900">
          {connected ? "已连接" : "未连接"}
        </span>
        <input
          className="h-8 w-72 rounded border border-line-200 px-2 text-xs focus:outline-none"
          placeholder="任务 ID（SSE）"
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
        />
        <input
          className="h-8 w-72 rounded border border-line-200 px-2 text-xs focus:outline-none"
          placeholder="文档 ID（图谱）"
          value={graphDocId}
          onChange={(e) => setGraphDocId(e.target.value)}
        />
        <span className="ml-auto text-xs text-ink-600">
          {taskDone && !status
            ? "done · 100%"
            : `${status?.status ?? taskInfo?.status ?? "—"} · ${Math.max(
                status?.progress ?? 0,
                taskInfo?.progress ?? 0,
              )}%`}
        </span>
        {taskError && (
          <p className="w-full rounded-md border border-risk-high/30 bg-[#FBF1EE] px-3 py-2 text-xs text-risk-highText">
            审查过程异常：{taskError}
          </p>
        )}
      </div>

      {/* 四栏联动：左聊天 + 右（画布/仪表盘/图谱） */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        {/* 聊天栏（1 栏） */}
        <div className="lg:col-span-1">
          <ChatPanel />
        </div>

        {/* 右侧三块 */}
        <div className="space-y-4 lg:col-span-3">
          {/* 仪表盘 */}
          <Dashboard status={status} tokenUsage={tokenUsage} task={taskInfo} risk={risk} />

          {/* 编排画布 + 数据流图谱并排 */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <OrchestrationCanvas
              activeNodes={activeNodes}
              done={taskDone || status?.status === "done"}
            />
            <div className="rounded-lg border border-line-200 bg-paper p-2">
              {graphDocId ? (
                <GraphPreview initialDocId={graphDocId} />
              ) : (
                <p className="flex h-[520px] items-center justify-center text-sm text-ink-400">
                  输入文档 ID 渲染数据流图谱
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
