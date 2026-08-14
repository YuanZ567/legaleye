"""模型配置契约模型（DATA_CONTRACT 4.2 Models）。"""

import uuid

from pydantic import Field

from app.core.enums import Provider
from app.schemas.base import APIModel


class ModelCreateIn(APIModel):
    """保存模型：{provider, apiKey, model}。"""

    provider: Provider
    api_key: str = Field(alias="apiKey", min_length=1)
    model: str = Field(min_length=1, max_length=64)


class ModelTestIn(APIModel):
    """测试模型：{provider, apiKey, model}。"""

    provider: Provider
    api_key: str = Field(alias="apiKey", min_length=1)
    model: str = Field(min_length=1, max_length=64)


class ModelOut(APIModel):
    """模型配置响应：{id, provider, displayName, model, apiKeyTail, isActive}。

    apiKeyTail 仅为末 4 位脱敏，绝不含明文 Key（L2 规则）。
    """

    id: uuid.UUID
    provider: Provider
    display_name: str = Field(alias="displayName")
    model: str
    api_key_tail: str = Field(alias="apiKeyTail")
    is_active: bool = Field(alias="isActive")


class ModelTestOut(APIModel):
    """测试响应：{ok, message?}。"""

    ok: bool
    message: str | None = None
