/** DiffView（DESIGN 8.3 专属组件）：整改 diff（原条款 vs 整改建议）。
 *
 * 使用 diff-match-patch 做字符级 diff（DESIGN 14.4）：
 * - 删除内容红底 #FEF3F2 左竖线 + <del> 划线；
 * - 新增内容绿底 #ECFDF3 + <ins>；
 * - 相同内容普通灰字。
 */

import { useMemo, type ReactNode } from "react";
import { diff_match_patch, DIFF_DELETE, DIFF_INSERT } from "diff-match-patch";

interface DiffViewProps {
  before: string;
  after: string;
}

/** diff-match-patch 计算字符级 diff 并返回渲染片段。 */
function computeDiff(before: string, after: string): ReactNode[] {
  const dmp = new diff_match_patch();
  const diffs = dmp.diff_main(before, after);
  dmp.diff_cleanupSemantic(diffs);

  return diffs.map(([op, text], idx) => {
    if (op === DIFF_DELETE) {
      return (
        <span
          key={idx}
          className="border-l-2 border-risk-high bg-[#FEF3F2] px-1 text-risk-highText line-through decoration-risk-highText/60"
        >
          {text}
        </span>
      );
    }
    if (op === DIFF_INSERT) {
      return (
        <span key={idx} className="border-l-2 border-risk-ok bg-[#ECFDF3] px-1 text-risk-ok">
          {text}
        </span>
      );
    }
    return <span key={idx}>{text}</span>;
  });
}

export default function DiffView({ before, after }: DiffViewProps) {
  const fragments = useMemo(() => computeDiff(before, after), [before, after]);
  return (
    <div className="space-y-2 text-sm leading-relaxed text-ink-600">
      <div className="rounded-md border border-line-200 bg-surface p-3">
        <div className="mb-1 text-xs font-medium text-ink-400">原条款 / 问题</div>
        <div className="whitespace-pre-wrap">{fragments}</div>
      </div>
      <div className="rounded-md border border-line-200 bg-surface p-3">
        <div className="mb-1 text-xs font-medium text-ink-400">整改建议</div>
        <div className="whitespace-pre-wrap">{after || "（无整改建议，需人工补充）"}</div>
      </div>
    </div>
  );
}
