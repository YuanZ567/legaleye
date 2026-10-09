/** 报告查看页（M9-2）：编辑式长文（DESIGN 7.3）。
 *
 * 结构：报告头（任务/审查时间/法规基线版本）→ 执行摘要（发现数、高风险数）
 * → 右侧固定目录（维度锚点 + 高风险数）→ 按维度分组结论（条款引用可点击跳知识库、
 * 版本、置信度、整改 diff）→ 跨文档矛盾区（联合审查）→ 免责声明。
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, FileText, AlertTriangle, CheckCircle, XCircle } from "lucide-react";

import { exportReportMarkdown, fetchReport } from "@/api/reports";
import type { Report, FindingContract, CrossDocConflict } from "@/api/types";
import RiskBadge from "@/components/RiskBadge";
import ClauseRef from "@/components/ClauseRef";
import DiffView from "@/components/DiffView";

interface ReportViewProps {
  taskId: string;
  onBack?: () => void;
}

/** 维度展示标签。 */
const DIMENSION_LABELS: Record<string, string> = {
  D1: "收集合规",
  D2: "存储与安全",
  D3: "处理目的",
  D4: "第三方与跨境",
  D5: "出境安全评估",
  D6: "用户权利响应",
  crossConsistency: "一致性校验",
};

function dimensionLabel(dim: string): string {
  return DIMENSION_LABELS[dim] ?? dim;
}

/** 按维度分组 findings。 */
function groupByDimension(findings: FindingContract[]): Record<string, FindingContract[]> {
  const grouped: Record<string, FindingContract[]> = {};
  for (const f of findings) {
    (grouped[f.dimension] ??= []).push(f);
  }
  return grouped;
}

function FindingItem({ finding }: { finding: FindingContract }) {
  return (
    <article className="rounded-xl border border-line-200 bg-card p-5 shadow-sm hover:shadow-md transition-shadow duration-200">
      {/* 结论头部：判定 + 等级 + 人工复核 */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-ink-900">{finding.verdict}</span>
        <RiskBadge level={finding.level} />
        {finding.needsHumanReview && (
          <span className="rounded-full border border-orange-200 bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700 flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            人工复核
          </span>
        )}
        <span className="ml-auto font-mono text-xs tabular-nums text-ink-600">
          置信度 {Math.round((finding.confidence ?? 0) * 100)}%
        </span>
      </div>

      {/* 条款引用 + 版本 */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <ClauseRef clauseRef={finding.clauseRef} statuteVersion={finding.statuteVersion} />
        {finding.statuteVersion && (
          <span className="font-mono text-xs text-ink-600">{finding.statuteVersion}</span>
        )}
      </div>

      {/* 问题描述 */}
      <p className="mt-3 text-sm leading-relaxed text-ink-900">
        {finding.description || "（待补）"}
      </p>

      {/* 证据原文 */}
      {finding.evidence?.text && (
        <blockquote className="mt-3 border-l-2 border-line-200 pl-3 text-xs italic leading-relaxed text-ink-600">
          {finding.evidence.text}
        </blockquote>
      )}

      {/* 整改 diff */}
      {finding.remediation && (
        <div className="mt-4 border-t border-line-100 pt-4">
          <div className="mb-2 text-xs font-medium text-ink-600">整改建议（diff）</div>
          <DiffView before={finding.description} after={finding.remediation} />
        </div>
      )}
    </article>
  );
}

function ConflictCard({ conflict }: { conflict: CrossDocConflict }) {
  return (
    <article className="rounded-xl border border-red-200 bg-red-50 p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-red-800">{conflict.declarationKey}</span>
        <RiskBadge level={conflict.level} />
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg bg-card p-3 shadow-sm">
          <div className="mb-1 text-xs font-medium text-ink-600">文档 A</div>
          <div className="text-sm text-ink-900">{conflict.docA.value || "（待补）"}</div>
          {conflict.docA.evidence?.text && (
            <div className="mt-1 text-xs italic text-ink-600">{conflict.docA.evidence.text}</div>
          )}
        </div>
        <div className="rounded-lg bg-card p-3 shadow-sm">
          <div className="mb-1 text-xs font-medium text-ink-600">文档 B</div>
          <div className="text-sm text-ink-900">{conflict.docB.value || "（待补）"}</div>
          {conflict.docB.evidence?.text && (
            <div className="mt-1 text-xs italic text-ink-600">{conflict.docB.evidence.text}</div>
          )}
        </div>
      </div>
    </article>
  );
}

export default function ReportView({ taskId, onBack }: ReportViewProps) {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // M10 修复：带 JWT 的 blob 下载（原 <a href> 直跳不带认证头 → 401 导不出）
  const handleExport = useCallback(async () => {
    setExporting(true);
    setExportError(null);
    try {
      await exportReportMarkdown(taskId);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "导出失败，请重试");
    } finally {
      setExporting(false);
    }
  }, [taskId]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReport(taskId);
      setReport(data);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "加载报告失败";
      // 404 → 报告未生成：任务可能仍在审查中，给出可操作的提示而非裸错误
      setError(
        /404|不存在/.test(msg)
          ? "报告尚未生成：任务可能仍在审查中或审查失败，请稍后点击「查询报告」重试（可在任务列表查看任务状态）"
          : msg,
      );
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    load();
  }, [load]);

  const grouped = useMemo(() => (report ? groupByDimension(report.findings ?? []) : {}), [report]);
  const dimensionOrder = useMemo(() => Object.keys(grouped), [grouped]);
  const conflicts = report?.crossDocConflicts ?? [];

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-ink-600">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent"></div>
          <span>加载报告中...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-12 text-center">
        <div className="rounded-full bg-red-100 p-3">
          <XCircle className="h-8 w-8 text-red-600" />
        </div>
        <div>
          <p className="text-sm text-red-700">{error}</p>
          <p className="mt-1 text-xs text-ink-600">请检查任务ID是否正确</p>
        </div>
        <button
          onClick={load}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors duration-200"
        >
          重新加载
        </button>
        {onBack && (
          <button
            onClick={onBack}
            className="text-sm text-ink-600 hover:text-ink-900 transition-colors duration-200"
          >
            返回
          </button>
        )}
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-12 text-center">
        <div className="rounded-full bg-secondary p-3">
          <FileText className="h-8 w-8 text-ink-600" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-ink-900">暂无报告</h3>
          <p className="mt-1 text-sm text-ink-600">请先生成合规审查任务</p>
        </div>
        {onBack && (
          <button
            onClick={onBack}
            className="text-sm text-brand-600 hover:text-brand-700 transition-colors duration-200"
          >
            返回任务列表
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-6xl gap-8 px-4">
      {/* 主内容列 */}
      <div className="min-w-0 flex-1">
        {/* 工具条：导出 Markdown / 返回 */}
        <div className="mb-6 flex items-center gap-2">
          {onBack && (
            <button
              onClick={onBack}
              className="inline-flex items-center gap-1 text-sm text-ink-600 hover:text-ink-900 transition-colors duration-200"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
              </svg>
              返回
            </button>
          )}
          <button
            onClick={handleExport}
            disabled={exporting}
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-line-200 bg-card px-3 py-2 text-sm font-medium text-ink-900 hover:bg-secondary transition-colors duration-200 shadow-sm disabled:opacity-60"
          >
            <Download className="h-4 w-4" />
            {exporting ? "导出中…" : "导出 Markdown"}
          </button>
        </div>
        {exportError && (
          <p className="mb-4 rounded-md border border-risk-high/30 bg-[#FBF1EE] px-3 py-2 text-xs text-risk-highText">
            导出失败：{exportError}
          </p>
        )}

        {/* 报告头 */}
        <header id="top" className="scroll-mt-24 border-b border-line-200 pb-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-ink-900">合规审查报告</h1>
              <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-ink-600">
                <div className="flex items-center gap-1">
                  <span className="font-medium text-ink-900">任务 ID:</span>
                  <span className="font-mono text-ink-900">{report.taskId}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="font-medium text-ink-900">审查时间:</span>
                  <span>{new Date(report.generatedAt).toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="font-medium text-ink-900">法规基线版本:</span>
                  <span className="font-mono text-brand-700">{report.baselineVersion}</span>
                </div>
              </div>
            </div>
            <div className="flex-shrink-0">
              <div className="rounded-lg bg-secondary p-3">
                <div className="text-xs font-medium text-ink-600">报告生成</div>
                <div className="text-sm font-semibold text-ink-900">
                  {new Date(report.generatedAt).toLocaleDateString()}
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* 执行摘要 */}
        <section id="summary" className="mt-6 scroll-mt-24">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-lg font-bold text-ink-900">执行摘要</h2>
            <div className="h-1 flex-1 bg-brand-600 rounded-full"></div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-line-200 bg-card p-5 shadow-sm">
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-secondary p-2">
                  <CheckCircle className="h-5 w-5 text-brand-600" />
                </div>
                <div>
                  <div className="text-xs text-ink-600">发现数</div>
                  <div className="mt-1 text-2xl font-bold tabular-nums text-ink-900">
                    {report.findingCount}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-line-200 bg-card p-5 shadow-sm">
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-red-100 p-2">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <div className="text-xs text-ink-600">高风险数</div>
                  <div className="mt-1 text-2xl font-bold tabular-nums text-red-600">
                    {report.highRiskCount}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-xl border border-line-200 bg-card p-4 shadow-sm">
            <p className="text-sm leading-relaxed text-ink-900">{report.summary}</p>
          </div>
        </section>

        {/* 跨文档矛盾区（联合审查） */}
        {conflicts.length > 0 && (
          <section id="conflicts" className="mt-8 scroll-mt-24">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-lg font-bold text-ink-900">跨文档矛盾</h2>
              <div className="h-1 flex-1 bg-risk-high rounded-full"></div>
            </div>

            <div className="space-y-4">
              {conflicts.map((c) => (
                <ConflictCard key={c.id} conflict={c} />
              ))}
            </div>
          </section>
        )}

        {/* 按维度分组结论 */}
        <section className="mt-8 space-y-6">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-lg font-bold text-ink-900">审查发现</h2>
            <div className="h-1 flex-1 bg-risk-ok rounded-full"></div>
          </div>

          {dimensionOrder.length === 0 ? (
            <div className="rounded-xl border border-line-200 bg-card p-8 text-center shadow-sm">
              <div className="mx-auto h-12 w-12 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="mt-4 text-lg font-medium text-ink-900">暂无审查发现</h3>
              <p className="mt-2 text-sm text-ink-600">该文档未发现合规问题</p>
            </div>
          ) : (
            dimensionOrder.map((dim) => (
              <section key={dim} id={`dim-${dim}`} className="scroll-mt-24">
                <div className="flex items-center gap-2 mb-4">
                  <h3 className="text-lg font-semibold text-ink-900">
                    {dimensionLabel(dim)}
                    <span className="ml-2 text-sm font-normal text-ink-600">
                      ({grouped[dim].length} 项)
                    </span>
                  </h3>
                  <div className="h-1 flex-1 bg-line-200 rounded-full"></div>
                </div>

                <div className="space-y-4">
                  {grouped[dim].map((f) => (
                    <FindingItem key={f.id} finding={f} />
                  ))}
                </div>
              </section>
            ))
          )}
        </section>

        {/* 免责声明 */}
        <footer className="mt-10 rounded-xl border border-line-200 bg-secondary p-6 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-secondary p-2 flex-shrink-0">
              <AlertTriangle className="h-5 w-5 text-brand-600" />
            </div>
            <div>
              <h3 className="font-semibold text-ink-900">免责声明</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-900">
                本报告由 LegalEye 法眼基于公开法规基线（{report.baselineVersion}）自动生成，
                仅供合规审查参考，不构成法律意见。高风险项与需人工复核项请由专业法律顾问最终确认。
              </p>
            </div>
          </div>
        </footer>
      </div>

      {/* 右侧固定目录 */}
      <aside className="sticky top-6 hidden w-64 shrink-0 lg:block">
        <div className="rounded-xl border border-line-200 bg-card p-5 shadow-sm sticky top-6">
          <div className="text-sm font-medium text-ink-900 mb-3">目录</div>

          <nav className="space-y-1">
            <a
              href="#top"
              className="block rounded-lg px-3 py-2 text-sm text-ink-900 hover:bg-secondary transition-colors duration-200"
            >
              报告头
            </a>
            <a
              href="#summary"
              className="block rounded-lg px-3 py-2 text-sm text-ink-900 hover:bg-secondary transition-colors duration-200"
            >
              执行摘要
            </a>

            {conflicts.length > 0 && (
              <a
                href="#conflicts"
                className="block rounded-lg px-3 py-2 text-sm text-ink-900 hover:bg-secondary transition-colors duration-200"
              >
                跨文档矛盾
              </a>
            )}

            <div className="mt-3 pt-3 border-t border-line-100">
              <div className="text-xs font-medium text-ink-600 mb-2">维度</div>
              {dimensionOrder.map((dim) => (
                <a
                  key={dim}
                  href={`#dim-${dim}`}
                  className="block truncate rounded-lg px-3 py-2 text-sm text-ink-900 hover:bg-secondary transition-colors duration-200"
                >
                  {dimensionLabel(dim)}
                </a>
              ))}
            </div>
          </nav>

          <div className="mt-4 pt-4 border-t border-line-100">
            <div className="text-xs font-medium text-ink-600 mb-1">高风险项</div>
            <div className="text-lg font-bold tabular-nums text-red-600">
              {report.highRiskCount}
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
