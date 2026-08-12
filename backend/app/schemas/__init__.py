"""API 契约模型包。

统一序列化：所有请求/响应模型继承 APIModel，输出 camelCase（DATA_CONTRACT 第 2 章）。
"""

from app.schemas.base import APIModel

__all__ = ["APIModel"]
