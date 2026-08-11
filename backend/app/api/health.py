"""健康检查路由（薄层：仅调用 services，不写业务逻辑）。"""

from fastapi import APIRouter

from app.services.health_service import check_health

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """健康检查：DB / Redis 连通状态。"""
    return await check_health()
