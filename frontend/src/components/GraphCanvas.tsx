/** 数据流图谱画布（M3-5，React Flow）：渲染实体/边，风险路径红色高亮。
 *
 * 配色对齐 DESIGN.md 4.2/4.4：
 *  - 实体角色描边：controller 青 #0E9384 / overseasReceiver 红 #D92D20 /
 *    dataCategory 墨灰 #475467（敏感转红）/ processor 青 / trustee 紫；
 *  - 边：crossBorder 红 #D92D20 实线加粗、is_risk 红加粗；其余按类型中性；
 *  - 风险路径（R1-R4 riskPaths）上的边红色高亮 + 脉冲描边动画。
 */

import { useMemo } from "react";
import { Background, BackgroundVariant, Controls, Handle, Position, ReactFlow } from "reactflow";
import "reactflow/dist/style.css";

import type {
  GraphEntity,
  GraphPayload,
} from "@/api/graph";

// ── DESIGN token 配色 ──
const ROLE_COLOR: Record<string, string> = {
  controller: "#0E9384", // 青
  processor: "#0E9384", // 青（中性操作）
  trustee: "#7A5AF8", // 紫
  overseasReceiver: "#D92D20", // 红（出境警示）
  dataCategory: "#475467", // 墨灰
};

const EDGE_COLOR: Record<string, string> = {
  collect: "#1570EF", // 蓝
  store: "#475467", // 灰
  share: "#0E9384", // 青
  entrust: "#7A5AF8", // 紫
  crossBorder: "#D92D20", // 红
  anonymize: "#12B76A", // 绿
};

const RISK_HIGH = "#D92D20";

/** 图谱实体节点：胶囊形 + 角色色描边；敏感数据类别加红点角标。 */
function EntityNode({ data }: { data: { entity: GraphEntity } }) {
  const { entity } = data;
  const stroke = entity.role === "dataCategory" && entity.isSensitive
    ? RISK_HIGH
    : ROLE_COLOR[entity.role] ?? "#8A93A6";
  return (
    <div
      className="rounded-full border-2 bg-white px-4 py-2 text-sm"
      style={{ borderColor: stroke, minWidth: 120, textAlign: "center" }}
    >
      {entity.isSensitive && (
        <span
          className="mr-1 inline-block h-2 w-2 rounded-full"
          style={{ backgroundColor: RISK_HIGH }}
          aria-label="敏感数据"
        />
      )}
      <span className="font-medium text-ink-900">{entity.name}</span>
      <span className="ml-1 text-xs text-ink-400">{entity.role}</span>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { entity: EntityNode };

interface Props {
  payload: GraphPayload | null;
  loading?: boolean;
  error?: string | null;
}

/** 图谱画布组件：输入 GraphPayload，渲染 React Flow 图。 */
export default function GraphCanvas({ payload, loading, error }: Props) {
  const { nodes, edges } = useMemo(() => {
    if (!payload) return { nodes: [], edges: [] };

    const riskEdgeIds = new Set(payload.riskPaths.flatMap((p) => p.edges));

    const nodes = payload.entities.map((entity, idx) => ({
      id: entity.id,
      type: "entity" as const,
      position: {
        x: 60 + (idx % 3) * 240,
        y: 60 + Math.floor(idx / 3) * 120,
      },
      data: { entity },
    }));

    const edges = payload.edges.map((edge) => {
      const isRisk = edge.isRisk || edge.type === "crossBorder" || riskEdgeIds.has(edge.id);
      const color = isRisk ? RISK_HIGH : EDGE_COLOR[edge.type] ?? "#8A93A6";
      return {
        id: edge.id,
        source: edge.from,
        target: edge.to,
        label: edge.type,
        style: {
          stroke: color,
          strokeWidth: isRisk ? 2.5 : 1.5,
        },
        className: isRisk ? "risk-edge" : undefined,
        labelStyle: { fontSize: 11, fill: color },
      };
    });

    return { nodes, edges };
  }, [payload]);

  if (loading) return <p className="p-6 text-sm text-ink-400">图谱加载中…</p>;
  if (error) return <p className="p-6 text-sm text-risk-highText">{error}</p>;
  if (!payload || nodes.length === 0) {
    return <p className="p-6 text-sm text-ink-400">暂无图谱数据</p>;
  }

  return (
    <div className="h-[520px] w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#E3E7EF" />
        <Controls />
      </ReactFlow>
      <style>{`
        .risk-edge path { stroke-dasharray: 8 4; animation: riskPulse 1.2s linear infinite; }
        @keyframes riskPulse { to { stroke-dashoffset: -12; } }
      `}</style>
    </div>
  );
}
