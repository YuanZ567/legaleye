"""API 层统一异常处理器：业务异常 → HTTP 状态码 + 契约错误体。

响应契约（DATA_CONTRACT 第 4 章）：失败统一 `{"error": {"code", "message"}}`。
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    DomainError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """注册业务异常 → HTTP 状态码映射。"""

    @app.exception_handler(DomainError)
    async def _domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        # 各异常子类的 HTTP 状态码映射
        status_map = {
            ValidationError: 400,
            NotFoundError: 404,
            ForbiddenError: 403,
            RateLimitError: 429,
        }
        # 显式 status_code 优先（如 OAuth 未配置 503）；否则用子类默认映射
        status = exc.status_code or status_map.get(type(exc), 400)
        return JSONResponse(status_code=status, content={"error": exc.to_dict()})
