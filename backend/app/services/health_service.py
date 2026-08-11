"""健康检查服务：验证基础设施连通性。"""

from sqlalchemy import create_engine, text

from app.core.config import get_settings


async def check_health() -> dict:
    """检查 DB / Redis 连通状态，返回分级结果。"""
    settings = get_settings()
    result: dict = {"status": "ok", "database": "unknown", "redis": "unknown"}

    # 数据库
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=2)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["database"] = "ok"
    except Exception:
        result["database"] = "error"

    # Redis
    try:
        from redis import asyncio as aioredis

        client = aioredis.from_url(settings.redis_url)
        try:
            await client.ping()
            result["redis"] = "ok"
        finally:
            await client.aclose()
    except Exception:
        result["redis"] = "error"

    if result["database"] == "error" or result["redis"] == "error":
        result["status"] = "degraded"
    return result
