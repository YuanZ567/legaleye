"""自定义业务异常体系（ARCHITECTURE 5.2）。

规则：
- 业务层（services 及以下）只抛本模块异常，禁止裸抛 HTTPException；
- 每个异常携带面向用户的 `message`（中文），由 API 层统一 Handler 转 HTTP 状态码；
- 响应契约（DATA_CONTRACT 第 4 章）：失败统一 `{"error": {"code", "message"}}`。
"""

from typing import Any


class DomainError(Exception):
    """业务异常基类。

    :param message: 面向用户的错误提示（中文）。
    :param code: 稳定错误码，默认取类名 snake_case。
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        extra: dict[str, Any] | None = None,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.extra = extra or {}
        # 可选自定义 HTTP 状态码（优先于子类默认映射，如 OAuth 未配置 → 503）
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        """转为响应契约中的 error 对象。"""
        return {"code": self.code, "message": self.message}


class ValidationError(DomainError):
    """参数/内容校验失败 → HTTP 400。"""


class NotFoundError(DomainError):
    """资源不存在 → HTTP 404。"""


class ForbiddenError(DomainError):
    """权限不足 → HTTP 403。"""


class RateLimitError(DomainError):
    """限流 → HTTP 429。"""


class LLMError(DomainError):
    """LLM 调用失败（M4 起使用）。"""
