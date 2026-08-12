"""图谱契约模型（DATA_CONTRACT 4.7 GraphPayload）。"""

import uuid
from typing import Any

from pydantic import Field

from app.core.enums import EdgeType, EntityRole, PathType, RiskLevel
from app.schemas.base import APIModel


class GraphEntity(APIModel):
    """图谱实体（4.7 entities）：{id, name, role, isSensitive?}。"""

    id: uuid.UUID
    name: str
    role: EntityRole
    is_sensitive: bool = Field(default=False, alias="isSensitive")


class GraphEdge(APIModel):
    """图谱边（4.7 edges）：{id, from, to, type, legalBasis?, isRisk}。"""

    id: uuid.UUID
    from_: str = Field(..., alias="from")  # 源实体 id
    to: str
    type: EdgeType
    legal_basis: str | None = Field(default=None, alias="legalBasis")
    is_risk: bool = Field(default=False, alias="isRisk")


class RiskPath(APIModel):
    """风险路径（4.7 riskPaths）：{id, path, edges, reason, level}。"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    path: list[str]  # 实体 id 序列
    edges: list[str]  # 边 id 序列
    reason: str
    level: RiskLevel


class Suggestion(APIModel):
    """路径判定建议（4.7 suggestions）：{pathType, advice, level}。"""

    path_type: PathType = Field(alias="pathType")
    advice: str
    level: RiskLevel


class GraphPayload(APIModel):
    """图谱完整载荷（4.7）。"""

    entities: list[GraphEntity] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    risk_paths: list[RiskPath] = Field(default_factory=list, alias="riskPaths")
    suggestions: list[Suggestion] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    def dump_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)
