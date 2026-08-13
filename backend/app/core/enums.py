"""枚举字典：唯一事实源为 docs/DATA_CONTRACT.md 第 3.1 节。

约定：枚举值即 API 传输值（camelCase），禁止在传输层再做值转换；
ORM 持久化时同样使用枚举值（见 models 中 sa.Enum 的 values_callable）。
"""

from enum import StrEnum


class DocType(StrEnum):
    """合规文档类型（DATA_CONTRACT 3.1 DocType 字典）。"""

    PRIVACY_POLICY = "privacyPolicy"
    USER_AGREEMENT = "userAgreement"
    DPA = "dpa"
    SCC = "scc"


class EntityRole(StrEnum):
    """图谱实体角色（DATA_CONTRACT 3.1 EntityRole 字典）。"""

    CONTROLLER = "controller"
    PROCESSOR = "processor"
    TRUSTEE = "trustee"
    OVERSEAS_RECEIVER = "overseasReceiver"
    DATA_CATEGORY = "dataCategory"


class EdgeType(StrEnum):
    """图谱边类型（DATA_CONTRACT 3.1 EdgeType 字典）。"""

    COLLECT = "collect"
    STORE = "store"
    SHARE = "share"
    ENTRUST = "entrust"
    CROSS_BORDER = "crossBorder"
    ANONYMIZE = "anonymize"


class RiskLevel(StrEnum):
    """风险等级（DATA_CONTRACT 3.1 RiskLevel 字典）。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PathType(StrEnum):
    """出境路径判定类型（DATA_CONTRACT 4.7 suggestions.pathType）。"""

    SECURITY_ASSESSMENT = "securityAssessment"
    SCC = "scc"
    CERTIFICATION = "certification"
    UNKNOWN = "unknown"


class Provider(StrEnum):
    """LLM Provider（ARCHITECTURE 6.2，四 provider 路由）。"""

    BAILIAN = "bailian"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ReviewDimension(StrEnum):
    """合规审查维度（DATA_CONTRACT 4.1 Dimension：D1-D6 + crossConsistency）。"""

    D1_COLLECTION = "d1Collection"
    D2_NOTICE = "d2Notice"
    D3_PURPOSE = "d3Purpose"
    D4_THIRD_PARTY = "d4ThirdParty"
    D5_CROSS_BORDER = "d5CrossBorder"
    D6_DATA_RIGHTS = "d6DataRights"
    CROSS_CONSISTENCY = "crossConsistency"


class FindingVerdict(StrEnum):
    """审查结论（DATA_CONTRACT 4.8 finding.verdict）。"""

    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "nonCompliant"
    NOT_APPLICABLE = "notApplicable"
    UNCLEAR = "unclear"


class FindingLevel(StrEnum):
    """风险等级（finding.level）。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
