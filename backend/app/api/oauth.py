"""OAuth API（M9-6）：GitHub 全链路 + QQ 接口就绪。

- GET /auth/oauth/{provider}/authorize → 302 跳第三方授权页（未配置凭据 503）；
- GET /auth/oauth/{provider}/callback → 校验 state → 换 token → 查/建用户 → 302 跳前端。

回调跳转地址来自 config.oauth_redirect_base（禁硬编码）。
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.services import oauth_service

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


@router.get("/{provider}/authorize")
async def oauth_authorize(provider: str) -> RedirectResponse:
    """发起第三方授权：生成 state（Redis TTL 300s）→ 302 跳授权页。

    凭据未配置返回 503（QQ 未开通时前端显示"暂未开通"）。
    """
    authorize_url = oauth_service.build_authorize_url(provider)
    return RedirectResponse(url=authorize_url, status_code=302)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),  # noqa: B008
) -> RedirectResponse:
    """回调：校验 state（防 CSRF）→ 换 token → 查/建用户 → 302 跳前端带 token。"""
    _, token = await oauth_service.handle_callback(provider, code, state, db)
    redirect_base = get_settings().oauth_redirect_base.rstrip("/")
    return RedirectResponse(url=f"{redirect_base}/oauth/callback?token={token}", status_code=302)
