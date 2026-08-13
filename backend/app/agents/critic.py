"""Critic 智能体（M5）：跨维度矛盾检测 + 高风险复核。

跨维度矛盾（规则引擎，确定性可测）：
- 声明-行为矛盾：文档声明与 D2/D4 finding 结论冲突；
- 不出境-图谱出境矛盾：文档声明"不出境"但图谱存在 crossBorder 风险路径；
- 高风险结论复核：needsHumanReview=true 的高风险 finding 联动标记（M5-2）。

输出：矛盾/复核 finding（维度=crossConsistency）+ 需打回的维度列表（反思循环用）。
"""

import logging

from app.core.sse import publish_event

logger = logging.getLogger(__name__)

# 声明"不出境"的关键词（用于检测 不出境-图谱出境 矛盾）
NO_OUTBOUND_KEYWORDS = ("不出境", "不向境外", "不跨境", "境内存储", "不提供境外")

# crossConsistency 维度的契约值
CROSS_DIM = "crossConsistency"


class Critic:
    """Critic 节点：跨维度矛盾检测 + 高风险复核。"""

    def __init__(self, *, document_declares_no_outbound: bool = False) -> None:
        self.declares_no_outbound = document_declares_no_outbound

    def analyze(
        self,
        *,
        task_id: str,
        findings: list[dict],
        graph_summary: str,
    ) -> tuple[list[dict], list[str]]:
        """执行 Critic 分析。

        :return: (新增 finding 列表, 需打回的维度列表)
        """
        publish_event(task_id, "nodeStart", {"node": "critic_agent", "dimension": CROSS_DIM})
        new_findings: list[dict] = []
        reconsider_dims: list[str] = []

        # 1) 不出境-图谱出境矛盾
        if self.declares_no_outbound and self._has_outbound_path(graph_summary):
            finding = self._conflict_finding(
                reason="文档声明不向境外提供，但图谱检测到出境路径",
                ref="待补",
            )
            new_findings.append(finding)
            reconsider_dims.append("d5")

        # 2) 声明-行为矛盾（D2 告知/同意 vs D5 跨境单独同意）
        d5_finding = self._find_dimension(findings, "d5")
        if d5_finding and d5_finding.get("verdict") == "nonCompliant":
            # 跨境不合规 + 图谱有出境 → 行为与义务矛盾（D5 已识别，强化 crossConsistency）
            if self._has_outbound_path(graph_summary):
                new_findings.append(
                    self._conflict_finding(
                        reason="存在跨境行为但跨境合规结论为不合规，行为与义务不一致",
                        ref=d5_finding.get("clauseRef", "待补"),
                    )
                )
                reconsider_dims.append("d5")

        # 3) 高风险结论复核（M5-2）：needsHumanReview=true 的高风险 finding 联动
        high_risk = [
            f
            for f in findings
            if f.get("needsHumanReview") and f.get("level") in ("high", "medium")
        ]
        if high_risk:
            for f in high_risk:
                new_findings.append(
                    self._conflict_finding(
                        reason=f"高风险结论待复核：维度 {f.get('dimension')} 需人工确认",
                        ref=f.get("clauseRef", "待补"),
                        human_review=True,
                    )
                )
            reconsider_dims.append("d1")  # 打回首维重审（简化：标记待复核）

        publish_event(task_id, "nodeEnd", {"node": "critic_agent", "dimension": CROSS_DIM})
        return new_findings, list(dict.fromkeys(reconsider_dims))

    # ── 辅助 ──
    @staticmethod
    def _conflict_finding(*, reason: str, ref: str, human_review: bool = False) -> dict:
        return {
            "dimension": CROSS_DIM,
            "verdict": "nonCompliant" if not human_review else "unclear",
            "level": "high" if not human_review else "medium",
            "clauseRef": ref,
            "statuteVersion": None,
            "description": reason,
            "remediation": "复核文档声明与图谱/各维度结论的一致性",
            "confidence": 0.0 if not human_review else 0.0,
            "needsHumanReview": human_review or True,
        }

    @staticmethod
    def _has_outbound_path(graph_summary: str) -> bool:
        """图谱摘要是否含出境风险路径（crossBorder）。

        排除"无/不存在"否定表达（如"（无出境风险路径）"），避免误判。
        """
        if not graph_summary:
            return False
        if any(
            kw in graph_summary for kw in ("（无", "无出境", "无跨境", "不存在出境", "无风险路径")
        ):
            return False
        # 有路径标记（"→"）或明确的 crossBorder/跨境 表达
        return "→" in graph_summary or "crossBorder" in graph_summary or "跨境" in graph_summary

    @staticmethod
    def _find_dimension(findings: list[dict], dim: str) -> dict | None:
        """按维度名（d1-d6 或契约值）查找 finding。"""
        for f in findings:
            if f.get("dimension") == dim or f.get("dimension") == _contract_dim(dim):
                return f
        return None


def _contract_dim(dim: str) -> str:
    """d1-d6 短名 → 契约维度值。"""
    return {
        "d1": "d1Collection",
        "d2": "d2Notice",
        "d3": "d3Purpose",
        "d4": "d4ThirdParty",
        "d5": "d5CrossBorder",
        "d6": "d6DataRights",
    }.get(dim, dim)
