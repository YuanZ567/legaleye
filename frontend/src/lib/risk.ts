/** 风险等级 → 展示映射（DESIGN 4.2 语义色 + DATA_CONTRACT 3.1 RiskLevel）。
 *
 * 颜色非唯一传达：RiskBadge 同时携带图标 + 文字 + 颜色。
 * 组件不散落色值，统一从本映射读取（DATA_CONTRACT 7.5）。
 */

import { AlertTriangle, Circle, CircleDot, CheckCircle2, MinusCircle } from "lucide-react";

import type { RiskLevel } from "@/api/types";

export interface RiskStyle {
  /** 主色（图形/描边，DESIGN 4.2）。 */
  color: string;
  /** 文字色（正文级，对比度 ≥4.5:1）。 */
  textColor: string;
  /** 底 / 边。 */
  bg: string;
  border: string;
  /** 中文标签。 */
  label: string;
  /** 图标。 */
  icon: typeof AlertTriangle;
}

const RISK_STYLES: Record<RiskLevel, RiskStyle> = {
  high: {
    color: "#D92D20",
    textColor: "#B42318",
    bg: "#FEF3F2",
    border: "#FDA29B",
    label: "高风险",
    icon: AlertTriangle,
  },
  medium: {
    color: "#DC6803",
    textColor: "#DC6803",
    bg: "#FFFAEB",
    border: "#FEC84B",
    label: "中风险",
    icon: CircleDot,
  },
  low: {
    color: "#1570EF",
    textColor: "#1570EF",
    bg: "#EFF8FF",
    border: "#84CAFF",
    label: "低风险",
    icon: Circle,
  },
  ok: {
    color: "#12B76A",
    textColor: "#12B76A",
    bg: "#ECFDF3",
    border: "#6CE9A6",
    label: "合规",
    icon: CheckCircle2,
  },
  pending: {
    color: "#98A2B3",
    textColor: "#98A2B3",
    bg: "#F2F4F7",
    border: "#D0D5DD",
    label: "待补",
    icon: MinusCircle,
  },
};

/** 按 level 取完整样式（缺省回退 pending）。 */
export function riskStyle(level?: RiskLevel): RiskStyle {
  return RISK_STYLES[level ?? "pending"] ?? RISK_STYLES.pending;
}
