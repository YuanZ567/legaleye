/** 知识库页（M9-5，M2 前端接线）：法条列表 + 语义检索。
 *
 * - 列表：GET /knowledge/laws（statute/articleNo/version/articleText）；
 * - 搜索：POST /knowledge/laws/search → Top-5 命中（条款号 + 原文 + 置信度）。
 */

import { useCallback, useEffect, useState } from "react";
import { Search } from "lucide-react";

import { fetchLaws, searchLaws } from "@/api/knowledge";
import type { LawBaseline, LawSearchHit } from "@/api/types";
import { Button } from "@/components/ui/button";

export default function KnowledgeBase() {
  const [laws, setLaws] = useState<LawBaseline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [hits, setHits] = useState<LawSearchHit[]>([]);
  const [searched, setSearched] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setLaws(await fetchLaws());
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载法条失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setSearched(true);
    try {
      setHits(await searchLaws(query.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "检索失败");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">知识库</h1>
        <p className="mt-1 text-sm text-ink-500">
          公开法规基线（PIPL / 网安法 / 数安法 / 出境评估与标准合同）。
        </p>
      </div>

      {/* 语义检索 */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入问题检索相关条款，如：跨境提供个人信息需满足哪些条件"
            className="h-9 w-full rounded-md border border-line-200 bg-surface pl-9 pr-3 text-sm focus:border-brand-600 focus:outline-none"
          />
        </div>
        <Button type="submit" disabled={searching || !query.trim()}>
          {searching ? "检索中…" : "检索"}
        </Button>
      </form>

      {/* 检索命中 */}
      {searched && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-ink-600">检索命中（Top-5）</h2>
          {hits.length === 0 ? (
            <p className="text-sm text-ink-400">未检索到相关条款。</p>
          ) : (
            hits.map((h, i) => (
              <div key={i} className="rounded-lg border border-brand-200 bg-brand-50/50 p-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-medium text-brand-700">
                    {h.clauseRef}
                  </span>
                  <span className="font-mono text-xs text-ink-400">
                    {h.statuteVersion} · {(h.score * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-ink-700">{h.articleText}</p>
              </div>
            ))
          )}
        </div>
      )}

      {error && (
        <p className="rounded-md border border-risk-high/30 bg-[#FEF3F2] px-3 py-2 text-sm text-risk-highText">
          {error}
        </p>
      )}

      {/* 法条列表 */}
      <div className="overflow-hidden rounded-lg border border-line-200 bg-surface">
        <div className="border-b border-line-200 bg-muted px-4 py-3 text-sm font-medium text-ink-500">
          法条基线（{laws.length} 条）
        </div>
        {loading ? (
          <p className="px-4 py-8 text-center text-sm text-ink-400">加载中…</p>
        ) : laws.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-ink-400">暂无法条</p>
        ) : (
          <div className="divide-y divide-line-100">
            {laws.map((law) => (
              <div key={law.id} className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-ink-900">{law.statute}</span>
                  <span className="font-mono text-xs text-brand-700">{law.articleNo}</span>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-ink-500">
                    {law.version}
                  </span>
                  <span className="ml-auto font-mono text-xs text-ink-400">
                    {law.effectiveDate}
                  </span>
                </div>
                <p className="mt-1 text-sm leading-relaxed text-ink-600">{law.articleText}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
