"""R1-R4 规则推理引擎（M3-4）：在已建图谱上执行路径检测与建议。

语义（计划书）：
- R1 出境可达路径：敏感数据类别 →（跳转）→ crossBorder 边 → 境外接收方；
- R2 未获单独同意出境：crossBorder 边缺少"单独同意"依据 → 高风险；
- R3 声明-图谱矛盾：文档声明不出境，但图谱存在 crossBorder 边 → 一致性冲突；
- R4 路径判定建议：按路径是否含敏感数据 / 是否授权，输出整改建议。

输出对齐 DATA_CONTRACT 4.7 RiskPath / Suggestion。
"""

from dataclasses import dataclass

import networkx as nx

from app.core.enums import PathType, RiskLevel

# 单独同意的关键词（用于 R2 判定 legal_basis 是否含同意依据）
CONSENT_KEYWORDS = ("同意", "单独同意", "授权", "知情同意")

# 默认路径深度上限（防止全图 BFS 爆炸）
MAX_PATH_LENGTH = 6


@dataclass
class RiskPathRecord:
    """R1/R2 推理出的风险路径记录（供 R4 汇总）。"""

    path: list[str]  # 实体名序列
    edge_ids: list[str]  # 边 id 序列
    reason: str  # 触发原因
    level: RiskLevel
    contains_sensitive: bool = False


class Reasoner:
    """基于 networkx 图的 R1-R4 推理。"""

    def __init__(self, graph: nx.DiGraph, *, declares_no_outbound: bool = False) -> None:
        self._g = graph
        self.declares_no_outbound = declares_no_outbound

    # ── R1：出境可达路径 ──
    def reachable_outbound_paths(self) -> list[RiskPathRecord]:
        """从敏感数据类别出发，找能到达境外接收方的可达路径（含 crossBorder 边）。

        数据流可达性用无向连通性判定（collect/store 等动作边方向不构成数据流向阻碍）；
        路径含 crossBorder 边即视为出境路径，标记是否含敏感数据。
        """
        sensitive_nodes = [n for n, d in self._g.nodes(data=True) if d.get("is_sensitive")]
        receiver_nodes = [
            n for n, d in self._g.nodes(data=True) if d.get("role") == "overseasReceiver"
        ]
        if not sensitive_nodes or not receiver_nodes:
            return []

        # 无向视图做连通性路径枚举（数据可达方向不强制）
        undirected = self._g.to_undirected()
        records: list[RiskPathRecord] = []
        for src in sensitive_nodes:
            for dst in receiver_nodes:
                for path in nx.all_simple_paths(undirected, src, dst, cutoff=MAX_PATH_LENGTH):
                    edge_ids, has_cross = self._path_edges(path)
                    if not has_cross:
                        continue
                    records.append(
                        RiskPathRecord(
                            path=[self._g.nodes[n]["name"] for n in path],
                            edge_ids=edge_ids,
                            reason="敏感数据存在出境可达路径",
                            level=RiskLevel.HIGH,
                            contains_sensitive=True,
                        )
                    )
        return records

    # ── R2：未获单独同意出境 ──
    def unauthorized_cross_border_edges(self) -> list[RiskPathRecord]:
        """crossBorder 边缺少单独同意依据 → 高风险。"""
        records: list[RiskPathRecord] = []
        for u, v, data in self._g.edges(data=True):
            if data.get("type") != "crossBorder":
                continue
            legal_basis = data.get("legal_basis") or ""
            consented = any(kw in legal_basis for kw in CONSENT_KEYWORDS)
            if not consented:
                records.append(
                    RiskPathRecord(
                        path=[self._g.nodes[u]["name"], self._g.nodes[v]["name"]],
                        edge_ids=[str(data.get("id"))],
                        reason="出境未经单独同意",
                        level=RiskLevel.HIGH,
                        contains_sensitive=bool(self._g.nodes[u].get("is_sensitive")),
                    )
                )
        return records

    # ── R3：声明-图谱矛盾 ──
    def declaration_conflict(self) -> list[RiskPathRecord]:
        """文档声明不出境但图谱存在 crossBorder 边 → 一致性冲突。"""
        if not self.declares_no_outbound:
            return []
        cross_edges = [
            (u, v, data)
            for u, v, data in self._g.edges(data=True)
            if data.get("type") == "crossBorder"
        ]
        return [
            RiskPathRecord(
                path=[self._g.nodes[u]["name"], self._g.nodes[v]["name"]],
                edge_ids=[str(data.get("id"))],
                reason="声明不向境外提供，但图谱存在出境行为",
                level=RiskLevel.HIGH,
            )
            for u, v, data in cross_edges
        ]

    # ── R4：路径判定建议 ──
    def suggestions(self, risk_records: list[RiskPathRecord]) -> list[dict]:
        """基于风险路径输出整改建议（对齐 4.7 suggestions）。"""
        suggestions: list[dict] = []
        has_sensitive_outbound = any(r.contains_sensitive for r in risk_records)
        if not risk_records:
            return suggestions

        if has_sensitive_outbound:
            suggestions.append(
                {
                    "pathType": PathType.SECURITY_ASSESSMENT,
                    "advice": "涉及敏感个人信息出境，建议通过国家网信部门安全评估",
                    "level": RiskLevel.HIGH,
                }
            )
            suggestions.append(
                {
                    "pathType": PathType.CERTIFICATION,
                    "advice": "或申请个人信息保护认证作为替代路径",
                    "level": RiskLevel.MEDIUM,
                }
            )
        else:
            suggestions.append(
                {
                    "pathType": PathType.SCC,
                    "advice": "建议与境外接收方订立标准合同（标准合同出境）",
                    "level": RiskLevel.MEDIUM,
                }
            )
        return suggestions

    # ── 辅助 ──
    def _path_edges(self, path: list) -> tuple[list[str], bool]:
        """返回路径上边 id 列表，及是否含 crossBorder 边。

        兼容无向路径：若正向无边则查反向边（数据流动作边方向不强制）。
        """
        edge_ids: list[str] = []
        has_cross = False
        for i in range(len(path) - 1):
            data = self._g.get_edge_data(path[i], path[i + 1])
            if data is None:
                data = self._g.get_edge_data(path[i + 1], path[i])
            if data is None:
                continue
            edge_ids.append(str(data.get("id")))
            if data.get("type") == "crossBorder":
                has_cross = True
        return edge_ids, has_cross
