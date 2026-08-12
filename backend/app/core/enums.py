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
