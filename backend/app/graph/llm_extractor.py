"""LLM 抽取通道（M3-3）：从文本抽取实体/关系，输出 EntitySpec/EdgeSpec。

设计：
- 定义 `ExtractionLLM` 协议（`extract(text) -> dict`），LLM 调用经此接口；
  真实实现（走 llm/factory，M4 接入）与 mock 可切换，保证可测试与 CI mock 纪律；
- `parse_llm_result`：解析 LLM 返回的 JSON（entities/edges），校验枚举/去重，非法值丢弃；
- LLM 调用记账由 M4 的 llm/factory 保证（本模块只负责结构化解析）。
"""

import logging
from dataclasses import dataclass
from typing import Protocol

from app.core.enums import EdgeType, EntityRole
from app.graph.builder import EdgeSpec, EntitySpec
from app.graph.rule_extractor import RuleExtraction

logger = logging.getLogger(__name__)


class ExtractionLLM(Protocol):
    """LLM 抽取接口：输入文本，返回结构化 dict（由 parse_llm_result 解析）。"""

    def extract(self, text: str) -> dict: ...


@dataclass
class LLMExtraction(RuleExtraction):
    """LLM 抽取结果（复用 RuleExtraction 结构，便于双通道合并）。"""


def parse_llm_result(raw: dict) -> LLMExtraction:
    """解析 LLM 返回的 JSON 结果，构造实体/边（非法值丢弃 + 告警）。

    期望格式：{"entities": [{"name", "role", "isSensitive"}],
               "edges": [{"source", "target", "edgeType", "legalBasis", "isRisk"}]}
    """
    result = LLMExtraction()

    # 实体
    for item in raw.get("entities", []):
        name = str(item.get("name", "")).strip()
        role_str = str(item.get("role", "")).strip()
        valid_role = role_str in EntityRole.__members__ or role_str in {e.value for e in EntityRole}
        if not name or not valid_role:
            logger.warning("LLM 实体非法，丢弃: %s", item)
            continue
        role = _to_role(role_str)
        result.entities.append(
            EntitySpec(name=name, role=role, is_sensitive=bool(item.get("isSensitive", False)))
        )

    # 边
    for item in raw.get("edges", []):
        source = str(item.get("source", "")).strip()
        target = str(item.get("target", "")).strip()
        type_str = str(item.get("edgeType", "")).strip()
        if not source or not target or type_str not in {e.value for e in EdgeType}:
            logger.warning("LLM 边非法，丢弃: %s", item)
            continue
        result.edges.append(
            EdgeSpec(
                source=source,
                target=target,
                edge_type=EdgeType(type_str),
                source_role=EntityRole.DATA_CATEGORY,  # 边端点角色由实体合并阶段确定
                target_role=EntityRole.DATA_CATEGORY,
                legal_basis=item.get("legalBasis") or None,
                is_risk=bool(item.get("isRisk", False)),
            )
        )

    result.dedup()
    return result


def _to_role(value: str) -> EntityRole:
    """枚举值字符串转 EntityRole（支持 camelCase 值）。"""
    for role in EntityRole:
        if role.value == value or role.name == value:
            return role
    raise ValueError(f"未知实体角色: {value}")


class MockExtractionLLM:
    """测试/CI 用的 mock LLM：返回预置结果或从文本启发式生成。

    真实 LLM 集成（走 llm/factory + 记账）留待 M4。
    """

    def __init__(self, canned: dict | None = None) -> None:
        self._canned = canned
        self.calls: list[str] = []  # 记录调用文本，便于断言调用路径

    def extract(self, text: str) -> dict:
        self.calls.append(text)
        if self._canned is not None:
            return self._canned
        # 默认启发式：空结果
        return {"entities": [], "edges": []}
