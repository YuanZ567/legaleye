/** 图谱预览页（M3-5）：输入文档 id 拉取数据流图谱并渲染 React Flow。
 *
 * 端到端：GET /documents/{id}/graph → GraphPayload → GraphCanvas。
 */

import { useCallback, useEffect, useState } from "react";

import { fetchDocumentGraph, type GraphPayload } from "@/api/graph";
import GraphCanvas from "@/components/GraphCanvas";

interface Props {
  /** 可选：初始文档 ID（自动加载，供工作台联动）。 */
  initialDocId?: string;
}

export default function GraphPreview({ initialDocId = "" }: Props) {
  const [docId, setDocId] = useState(initialDocId);
  const [payload, setPayload] = useState<GraphPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadGraph = useCallback(async () => {
    if (!docId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDocumentGraph(docId.trim());
      setPayload(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [docId]);

  // 初始文档 ID 变化时自动加载
  useEffect(() => {
    if (initialDocId && initialDocId !== docId) {
      setDocId(initialDocId);
    }
    if (initialDocId) {
      loadGraph();
    }
  }, [initialDocId, docId, loadGraph]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <input
          className="h-9 flex-1 rounded-md border border-line-200 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-600"
          placeholder="输入文档 ID（如真实 PG 中的文档 uuid）"
          value={docId}
          onChange={(e) => setDocId(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && loadGraph()}
        />
        <button
          className="h-9 rounded-md bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          onClick={loadGraph}
          disabled={loading || !docId.trim()}
        >
          渲染图谱
        </button>
      </div>

      {payload?.suggestions && payload.suggestions.length > 0 && (
        <div className="rounded-lg border border-line-200 bg-surface p-4">
          <p className="mb-2 text-sm font-medium text-ink-900">整改建议（R4）</p>
          {payload.suggestions.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span
                className="rounded px-2 py-0.5 text-xs"
                style={{ backgroundColor: s.level === "high" ? "#FEF3F2" : "#FFFAEB" }}
              >
                {s.pathType}
              </span>
              <span className="text-ink-600">{s.advice}</span>
            </div>
          ))}
        </div>
      )}

      {payload?.riskPaths && payload.riskPaths.length > 0 && (
        <div className="rounded-lg border border-line-200 bg-surface p-4">
          <p className="mb-2 text-sm font-medium text-ink-900">风险路径（R1-R4）</p>
          {payload.riskPaths.map((p, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span
                className="rounded px-2 py-0.5 text-xs font-medium"
                style={{
                  backgroundColor: "#FEF3F2",
                  color: "#B42318",
                }}
              >
                {p.level}
              </span>
              <span className="text-ink-600">{p.path.join(" → ")}</span>
              <span className="text-ink-400">{p.reason}</span>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-lg border border-line-200 bg-paper">
        <GraphCanvas payload={payload} loading={loading} error={error} />
      </div>
    </div>
  );
}
