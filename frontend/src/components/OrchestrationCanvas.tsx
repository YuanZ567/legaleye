/** 编排画布（M7-2）：React Flow 渲染 LangGraph 编排图（D1-D6 + Critic）。
 *
 * 节点 = 维度智能体；边 = 数据流（或chestrator→维度→critic→反思）。
 * 节点状态着色（DESIGN 14.2）：running 蓝 #1570EF / done 绿 #12B76A / failed 红 #D92D20。
 */

import { useMemo } from "react";
import { Background, BackgroundVariant, Controls, Handle, Position, ReactFlow } from "reactflow";
import "reactflow/dist/style.css";

import type { NodeEvent } from "@/api/types";

// 编排节点定义（固定布局：orchestrator → 六维 → critic）
const STAGES = [
  { id: "orchestrator", label: "Orchestrator 编排", x: 40, y: 240 },
  { id: "d1", label: "D1 收集", x: 260, y: 40 },
  { id: "d2", label: "D2 告知同意", x: 260, y: 130 },
  { id: "d3", label: "D3 目的最小化", x: 260, y: 220 },
  { id: "d4", label: "D4 第三方委托", x: 260, y: 310 },
  { id: "d5", label: "D5 跨境", x: 260, y: 400 },
  { id: "d6", label: "D6 权利响应", x: 260, y: 490 },
  { id: "critic", label: "Critic 复核", x: 500, y: 240 },
];

// 节点 → 智能体名（SSE nodeStart/nodeEnd 的 node 字段）
const AGENT_NAME: Record<string, string> = {
  orchestrator: "orchestrator",
  d1: "collection_agent",
  d2: "notice_consent_agent",
  d3: "purpose_minimization_agent",
  d4: "third_party_agent",
  d5: "cross_border_agent",
  d6: "data_rights_agent",
  critic: "critic_agent",
};

interface Props {
  /** 运行中节点（SSE nodeStart 累积）。 */
  activeNodes: NodeEvent[];
  /** 任务是否完成（全绿）。 */
  done?: boolean;
}

function StageNode({ data }: { data: { label: string; state: string } }) {
  const color =
    data.state === "running" ? "#1570EF" : data.state === "done" ? "#12B76A" : data.state === "failed" ? "#D92D20" : "#8A93A6";
  return (
    <div
      className="rounded-lg border-2 bg-card px-3 py-2 text-sm"
      style={{ borderColor: color, minWidth: 110, textAlign: "center" }}
    >
      <span className="font-medium" style={{ color }}>
        {data.label}
      </span>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { stage: StageNode };

export default function OrchestrationCanvas({ activeNodes, done }: Props) {
  const runningSet = useMemo(
    () => new Set(activeNodes.map((n) => n.node)),
    [activeNodes],
  );

  const nodes = STAGES.map((s) => ({
    id: s.id,
    type: "stage" as const,
    position: { x: s.x, y: s.y },
    data: {
      label: s.label,
      state: done ? "done" : runningSet.has(AGENT_NAME[s.id]) ? "running" : "idle",
    },
  }));

  const edges = [
    ...STAGES.slice(1, 7).map((s) => ({
      id: `e-orch-${s.id}`,
      source: "orchestrator",
      target: s.id,
    })),
    ...STAGES.slice(1, 7).map((s) => ({
      id: `e-${s.id}-critic`,
      source: s.id,
      target: "critic",
    })),
  ];

  return (
    <div className="h-[520px] w-full rounded-lg border border-line-200 bg-surface">
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
    </div>
  );
}
