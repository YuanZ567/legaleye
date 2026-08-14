/** ClauseRef（DESIGN 8.2 专属组件）：条款引用 chip。
 *
 * - IBM Plex Mono 13px + 链接 icon；
 * - hover 弹 tooltip 显示法规版本；
 * - 点击跳转知识库原文（新标签，URL 携带 statute 关键词）。
 */

import { ExternalLink } from "lucide-react";

interface ClauseRefProps {
  clauseRef: string;
  statuteVersion?: string | null;
}

/** 由 statuteVersion（如 "个人信息保护法(2021)"）提取法规名关键词。 */
function extractStatute(statuteVersion?: string | null): string {
  if (!statuteVersion) return "";
  return statuteVersion.replace(/\(.*\)$/, "").trim();
}

export default function ClauseRef({ clauseRef, statuteVersion }: ClauseRefProps) {
  const href = `/admin/knowledge?statute=${encodeURIComponent(extractStatute(statuteVersion))}`;
  return (
    <span className="group relative inline-flex items-center">
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 rounded border border-brand-200 bg-brand-50 px-2 py-0.5 font-mono text-[13px] font-medium text-brand-700 transition-colors hover:bg-brand-100 hover:text-brand-800"
      >
        {clauseRef || "待补"}
        <ExternalLink className="h-3 w-3" />
      </a>
      {statuteVersion && (
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1.5 hidden -translate-x-1/2 whitespace-nowrap rounded-md bg-ink-900 px-2.5 py-1 text-xs text-white shadow-sm group-hover:block"
        >
          {statuteVersion}
          <span className="absolute left-1/2 top-full h-2 w-2 -translate-x-1/2 -translate-y-1 rotate-45 bg-ink-900" />
        </span>
      )}
    </span>
  );
}
