"""LegalEye 后端入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    documents,
    graph,
    health,
    knowledge,
    models,
    oauth,
    reports,
    tasks,
    user_api_key,
)
from app.api.errors import register_exception_handlers
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期钩子（M4 起在此初始化连接池等）。

    M10+ 账户管理：启动时对 users 表做轻量自动补列（display_name/avatar），
    避免 alembic 之外的历史库缺列导致接口 500；列已存在则跳过。
    """
    from sqlalchemy import inspect, text

    from app.core.db import engine

    try:
        inspector = inspect(engine)
        if inspector.has_table("users"):
            existing = {col["name"] for col in inspector.get_columns("users")}
            with engine.begin() as conn:
                if "display_name" not in existing:
                    conn.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(64)"))
                if "avatar" not in existing:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar VARCHAR(16)"))
    except Exception:  # noqa: BLE001 — 补列失败不阻断启动（首次建表场景由 create_all 覆盖）
        pass
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="LegalEye API",
        description="出海企业数据合规智能审查多智能体系统",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(knowledge.router)
    app.include_router(graph.router)
    app.include_router(models.router)
    app.include_router(tasks.router)
    app.include_router(reports.router)
    app.include_router(oauth.router)
    app.include_router(user_api_key.router)
    register_exception_handlers(app)
    return app


app = create_app()
