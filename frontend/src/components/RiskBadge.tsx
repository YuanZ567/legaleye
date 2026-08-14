/** RiskBadge（DESIGN 8.1 专属组件 + 4.2 语义色）。
 *
 * 胶囊 pill；同时以 图标 + 文字 + 颜色 呈现风险等级（颜色非唯一传达，色觉障碍不丢信息）。
 */

import { cn } from "@/lib/utils";
import { riskStyle } from "@/lib/risk";
import type { RiskLevel } from "@/api/types";

interface RiskBadgeProps {
  level?: RiskLevel;
  label?: string;
  className?: string;
}

export default function RiskBadge({ level, label, className }: RiskBadgeProps) {
  const style = riskStyle(level);
  const Icon = style.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        className,
      )}
      style={{ backgroundColor: style.bg, borderColor: style.border, color: style.textColor }}
    >
      <Icon className="h-3 w-3" strokeWidth={2.5} />
      {label ?? style.label}
    </span>
  );
}
