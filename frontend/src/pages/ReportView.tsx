/** 报告查看页（M9-2）：编辑式长文（DESIGN 7.3）。
 *
 * 结构：报告头（任务/审查时间/法规基线版本）→ 执行摘要（发现数、高风险数）
 * → 右侧固定目录（维度锚点 + 高风险数）→ 按维度分组结论（条款引用可点击跳知识库、
 * 版本、置信度、整改 diff）→ 跨文档矛盾区（联合审查）→ 免责声明。
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, FileText } from "lucide-react";

import { fetchReport, reportMarkdownUrl } from "@/api/reports";
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
    <article className="rounded-lg border border-line-200 bg-surface p-5">
      {/* 结论头部：判定 + 等级 + 人工复核 */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-ink-900">{finding.verdict}</span>
        <RiskBadge level={finding.level} />
        {finding.needsHumanReview && (
          <span className="rounded-full border border-risk-medium bg-[#FFFAEB] px-2 py-0.5 text-xs font-medium text-risk-medium">
            需人工复核
          </span>
        )}
        <span className="ml-auto font-mono text-xs tabular-nums text-ink-400">
          置信度 {Math.round((finding.confidence ?? 0) * 100)}%
        </span>
      </div>

      {/* 条款引用 + 版本 */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <ClauseRef clauseRef={finding.clauseRef} statuteVersion={finding.statuteVersion} />
        {finding.statuteVersion && (
          <span className="font-mono text-xs text-ink-400">{finding.statuteVersion}</span>
        )}
      </div>

      {/* 问题描述 */}
      <p className="mt-3 text-sm leading-relaxed text-ink-600">
        {finding.description || "（待补）"}
      </p>

      {/* 证据原文 */}
      {finding.evidence?.text && (
        <blockquote className="mt-3 border-l-2 border-line-200 pl-3 text-xs italic leading-relaxed text-ink-400">
          {finding.evidence.text}
        </blockquote>
      )}

      {/* 整改 diff */}
      {finding.remediation && (
        <div className="mt-4 border-t border-line-100 pt-4">
          <div className="mb-2 text-xs font-medium text-ink-400">整改建议（diff）</div>
          <DiffView before={finding.description} after={finding.remediation} />
        </div>
      )}
    </article>
  );
}

function ConflictCard({ conflict }: { conflict: CrossDocConflict }) {
  return (
    <article className="rounded-lg border border-risk-high/30 bg-[#FEF3F2] p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-risk-highText">{conflict.declarationKey}</span>
        <RiskBadge level={conflict.level} />
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="rounded-md bg-surface p-3">
          <div className="mb-1 text-xs font-medium text-ink-400">文档 A</div>
          <div className="text-sm text-ink-700">{conflict.docA.value || "（待补）"}</div>
          {conflict.docA.evidence?.text && (
            <div className="mt-1 text-xs italic text-ink-400">{conflict.docA.evidence.text}</div>
          )}
        </div>
        <div className="rounded-md bg-surface p-3">
          <div className="mb-1 text-xs font-medium text-ink-400">文档 B</div>
          <div className="text-sm text-ink-700">{conflict.docB.value || "（待补）"}</div>
          {conflict.docB.evidence?.text && (
            <div className="mt-1 text-xs italic text-ink-400">{conflict.docB.evidence.text}</div>
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

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReport(taskId);
      setReport(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载报告失败");
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
      <div className="flex h-full items-center justify-center text-sm text-ink-400">
        加载报告中…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
        <p className="text-sm text-risk-highText">{error}</p>
        <button
          onClick={load}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          重试
        </button>
        {onBack && (
          <button onClick={onBack} className="text-sm text-ink-500 hover:text-ink-700">
            返回
          </button>
        )}
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
        <FileText className="h-8 w-8 text-ink-400" />
        <p className="text-sm text-ink-500">暂无报告，请先生成审查任务</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-[1200px] gap-8 px-2">
      {/* 主内容列（DESIGN 7.3：max-width 820px） */}
      <div className="min-w-0 flex-1">
        {/* 工具条：导出 Markdown / 返回 */}
        <div className="mb-4 flex items-center gap-2">
          {onBack && (
            <button onClick={onBack} className="text-sm text-ink-500 hover:text-ink-700">
              ← 返回
            </button>
          )}
          <a
            href={reportMarkdownUrl(taskId)}
            className="ml-auto inline-flex items-center gap-1.5 rounded-md border border-line-200 bg-surface px-3 py-1.5 text-sm font-medium text-ink-600 hover:bg-muted"
          >
            <Download className="h-4 w-4" />
            导出 Markdown
          </a>
        </div>

        {/* 报告头 */}
        <header id="top" className="scroll-mt-24 border-b border-line-200 pb-6">
          <h1 className="text-2xl font-semibold text-ink-900">合规审查报告</h1>
          <dl className="mt-4 space-y-1.5 text-sm text-ink-600">
            <div className="flex gap-2">
              <dt className="w-28 shrink-0 text-ink-400">任务 ID</dt>
              <dd className="font-mono text-xs text-ink-600">{report.taskId}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-28 shrink-0 text-ink-400">审查时间</dt>
              <dd>{new Date(report.generatedAt).toLocaleString()}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-28 shrink-0 text-ink-400">法规基线版本</dt>
              <dd className="font-mono text-xs text-brand-700">{report.baselineVersion}</dd>
            </div>
          </dl>
        </header>

        {/* 执行摘要 */}
        <section id="summary" className="mt-6 scroll-mt-24">
          <h2 className="text-lg font-semibold text-ink-900">执行摘要</h2>
          <div className="mt-3 flex gap-4">
            <div className="flex-1 rounded-lg border border-line-200 bg-surface p-4">
              <div className="text-xs text-ink-400">发现数</div>
              <div className="mt-1 text-2xl font-semibold tabular-nums text-ink-900">
                {report.findingCount}
              </div>
            </div>
            <div className="flex-1 rounded-lg border border-line-200 bg-surface p-4">
              <div className="text-xs text-ink-400">高风险数</div>
              <div className="mt-1 text-2xl font-semibold tabular-nums text-risk-highText">
                {report.highRiskCount}
              </div>
            </div>
          </div>
          <p className="mt-4 text-sm leading-relaxed text-ink-600">{report.summary}</p>
        </section>

        {/* 跨文档矛盾区（联合审查） */}
        {conflicts.length > 0 && (
          <section id="conflicts" className="mt-8 scroll-mt-24">
            <h2 className="text-lg font-semibold text-ink-900">跨文档矛盾</h2>
            <div className="mt-3 space-y-3">
              {conflicts.map((c) => (
                <ConflictCard key={c.id} conflict={c} />
              ))}
            </div>
          </section>
        )}

        {/* 按维度分组结论 */}
        <section className="mt-8 space-y-8">
          {dimensionOrder.length === 0 && <p className="text-sm text-ink-400">暂无审查发现。</p>}
          {dimensionOrder.map((dim) => (
            <section key={dim} id={`dim-${dim}`} className="scroll-mt-24">
              <h2 className="border-b border-line-200 pb-2 text-lg font-semibold text-ink-900">
                {dimensionLabel(dim)}
                <span className="ml-2 text-sm font-normal text-ink-400">
                  {grouped[dim].length} 项
                </span>
              </h2>
              <div className="mt-3 space-y-3">
                {grouped[dim].map((f) => (
                  <FindingItem key={f.id} finding={f} />
                ))}
              </div>
            </section>
          ))}
        </section>

        {/* 免责声明 */}
        <footer className="mt-10 rounded-lg border border-line-200 bg-muted/50 p-4 text-xs leading-relaxed text-ink-400">
          <p className="font-medium text-ink-600">免责声明</p>
          <p className="mt-1">
            本报告由 LegalEye 法眼基于公开法规基线（{report.baselineVersion}
            ）自动生成，仅供合规审查参考，不构成法律意见。高风险项与需人工复核项请由专业法律顾问最终确认。
          </p>
        </footer>
      </div>

      {/* 右侧固定目录（DESIGN 7.3） */}
      <aside className="sticky top-6 hidden w-52 shrink-0 lg:block">
        <div className="rounded-lg border border-line-200 bg-surface p-4">
          <div className="text-xs font-medium text-ink-400">目录</div>
          <nav className="mt-2 space-y-1">
            <a href="#top" className="block rounded px-2 py-1 text-sm text-ink-600 hover:bg-muted">
              报告头
            </a>
            <a
              href="#summary"
              className="block rounded px-2 py-1 text-sm text-ink-600 hover:bg-muted"
            >
              执行摘要
            </a>
            {conflicts.length > 0 && (
              <a
                href="#conflicts"
                className="block rounded px-2 py-1 text-sm text-ink-600 hover:bg-muted"
              >
                跨文档矛盾
              </a>
            )}
            <div className="mt-1 pt-1 text-xs font-medium text-ink-400">维度</div>
            {dimensionOrder.map((dim) => (
              <a
                key={dim}
                href={`#dim-${dim}`}
                className="block truncate rounded px-2 py-1 text-sm text-ink-600 hover:bg-muted"
              >
                {dimensionLabel(dim)}
              </a>
            ))}
          </nav>
          <div className="mt-3 border-t border-line-100 pt-3 text-xs text-ink-400">
            高风险{" "}
            <span className="font-semibold tabular-nums text-risk-highText">
              {report.highRiskCount}
            </span>
          </div>
        </div>
      </aside>
    </div>
  );
}
