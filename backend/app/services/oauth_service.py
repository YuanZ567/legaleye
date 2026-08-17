"""OAuth 服务（M9-6）：GitHub 全链路 + QQ 接口就绪。

流程：
1. authorize(provider) → 生成随机 state 存 Redis（TTL 300s）→ 302 跳第三方授权页；
2. callback(provider, code, state) → 校验 state（防 CSRF，Redis 一次性）→ httpx 换 token
   → 拉第三方用户 → 按 (provider, oauth_id) 查/建本系统用户 → 签 JWT。

红线（任务包）：
- state 必须校验（Redis TTL 300s），防 CSRF；
- OAuth 用户合成邮箱 {provider}_{oauth_id}@oauth.local、role 一律 user、不触发首个 admin；
- 凭据只来自 config（.env），禁硬编码；
- 回调地址可配置（config.oauth_redirect_base / api_base_url），禁硬编码。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import create_access_token
from app.core.config import get_settings
from app.core.enums import UserRole
from app.core.exceptions import ValidationError
from app.models import User

SUPPORTED_PROVIDERS = ("github", "qq")


def _redis():
    """Redis 客户端（OAuth state 强依赖，不可用抛异常，不允许降级——安全红线）。"""
    import redis

    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def _state_key(provider: str, state: str) -> str:
    return f"oauth:state:{provider}:{state}"


def _save_state(provider: str, state: str) -> None:
    """存 state（TTL 300s）。"""
    client = _redis()
    ttl = get_settings().oauth_state_ttl_seconds
    client.set(_state_key(provider, state), "1", ex=ttl)


def _consume_state(provider: str, state: str) -> bool:
    """校验并一次性消费 state（存在返回 True 并删除）。"""
    client = _redis()
    key = _state_key(provider, state)
    ok = client.get(key) is not None
    if ok:
        client.delete(key)
    return ok


def _provider_configured(provider: str) -> bool:
    """provider 凭据是否已配置（GitHub/QQ；未配置返回 False → authorize 503）。"""
    s = get_settings()
    if provider == "github":
        return bool(s.github_client_id and s.github_client_secret)
    if provider == "qq":
        return bool(s.qq_app_id and s.qq_app_key)
    return False


def build_authorize_url(provider: str) -> str:
    """生成 state 并返回第三方授权 URL。凭据未配置抛 503。"""
    if provider not in SUPPORTED_PROVIDERS:
        raise ValidationError(f"不支持的 OAuth provider: {provider}", code="oauth_unsupported")
    if not _provider_configured(provider):
        raise ValidationError(
            f"{provider} 未配置凭据，暂未开通", code="oauth_not_configured", status_code=503
        )
    s = get_settings()
    state = uuid.uuid4().hex
    _save_state(provider, state)
    redirect_uri = f"{s.api_base_url}/auth/oauth/{provider}/callback"

    if provider == "github":
        return (
            "https://github.com/login/oauth/authorize"
            f"?client_id={s.github_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
        )
    # QQ
    return (
        "https://graph.qq.com/oauth2.0/authorize"
        f"?response_type=code&client_id={s.qq_app_id}"
        f"&redirect_uri={redirect_uri}&state={state}"
    )


async def _github_exchange_and_fetch(code: str, redirect_uri: str) -> dict:
    """GitHub：换 token → 拉用户。返回 {oauth_id, email?, display_name?}。"""
    import httpx

    s = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": s.github_client_id,
                "client_secret": s.github_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_json = token_resp.json()
        access_token = token_json.get("access_token")
        if not access_token:
            raise ValidationError("GitHub 换取 token 失败", code="oauth_token_error")

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        user_resp.raise_for_status()
        user_json = user_resp.json()
        return {
            "oauth_id": str(user_json["id"]),
            "display_name": user_json.get("name") or user_json.get("login") or "github_user",
        }


async def _qq_exchange_and_fetch(code: str, redirect_uri: str) -> dict:
    """QQ：换 token → 取 openid（凭据留空时本函数不会被调到，因 authorize 已 503）。"""
    import httpx

    s = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.get(
            "https://graph.qq.com/oauth2.0/token",
            params={
                "grant_type": "authorization_code",
                "client_id": s.qq_app_id,
                "client_secret": s.qq_app_key,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        token_resp.raise_for_status()
        # QQ 返回 "access_token=xxx&expires_in=..."（或 JSON）
        import urllib.parse

        params = dict(urllib.parse.parse_qsl(token_resp.text))
        access_token = params.get("access_token")
        if not access_token:
            raise ValidationError("QQ 换取 token 失败", code="oauth_token_error")

        me_resp = await client.get(
            "https://graph.qq.com/oauth2.0/me", params={"access_token": access_token}
        )
        me_resp.raise_for_status()
        # 返回 "callback( {\"client_id\":\"...\",\"openid\":\"...\"} );"
        text = me_resp.text
        start, end = text.find("("), text.rfind(")")
        openid = ""
        if start != -1 and end != -1:
            import json

            openid = json.loads(text[start + 1 : end]).get("openid", "")
        if not openid:
            raise ValidationError("QQ 获取 openid 失败", code="oauth_openid_error")
        return {"oauth_id": openid, "display_name": "qq_user"}


async def handle_callback(provider: str, code: str, state: str, db: Session) -> tuple[User, str]:
    """回调：校验 state → 换 token → 拉用户 → 查/建用户 → 签 JWT。返回 (user, token)。"""
    if provider not in SUPPORTED_PROVIDERS:
        raise ValidationError(f"不支持的 OAuth provider: {provider}", code="oauth_unsupported")
    if not _consume_state(provider, state):
        raise ValidationError("OAuth state 校验失败", code="oauth_state_invalid", status_code=400)

    s = get_settings()
    redirect_uri = f"{s.api_base_url}/auth/oauth/{provider}/callback"

    if provider == "github":
        info = await _github_exchange_and_fetch(code, redirect_uri)
    else:
        info = await _qq_exchange_and_fetch(code, redirect_uri)

    user = _find_or_create(db, provider, info["oauth_id"])
    token = create_access_token(user.id, user.role)
    return user, token


def _find_or_create(db: Session, provider: str, oauth_id: str) -> User:
    """按 (provider, oauth_id) 查用户；不存在则建（role 一律 user，不触发首个 admin）。"""
    user = db.scalar(select(User).where(User.oauth_provider == provider, User.oauth_id == oauth_id))
    if user is not None:
        return user
    email = f"{provider}_{oauth_id}@oauth.local"
    user = User(
        email=email,
        password_hash="",  # OAuth 用户无密码（email unique 约束仍满足：合成邮箱唯一）
        role=UserRole.USER,
        oauth_provider=provider,
        oauth_id=oauth_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
