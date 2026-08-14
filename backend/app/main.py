"""LegalEye 后端入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, documents, graph, health, knowledge, models, tasks
from app.api.errors import register_exception_handlers
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期钩子（M4 起在此初始化连接池等）。"""
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
    register_exception_handlers(app)
    return app


app = create_app()
