"""API 模型基类：统一 camelCase 序列化。

规则（DATA_CONTRACT 第 2 章）：
- alias_generator=to_camel：序列化/校验时字段名输出 camelCase；
- populate_by_name=True：允许 snake_case 入参（后端内部保持一致）；
- use_enum_values=True：枚举序列化为原始字符串值。
"""

from pydantic import BaseModel, ConfigDict, alias_generators


class APIModel(BaseModel):
    """所有请求/响应模型的基类。"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
        use_enum_values=True,
    )
