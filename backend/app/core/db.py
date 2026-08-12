"""数据库基础设施：引擎与会话工厂（FastAPI 依赖注入）。

纪律（ARCHITECTURE 红线）：
- 禁止直连 DB / 业务层直接 import engine 做原生 SQL；
- 所有业务查询必须集中在 services/（repository 风格）中实现；
- 本文件只提供"会话工厂"，不承载任何业务逻辑。
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# 全局单例引擎：pool_pre_ping 保证连接在长会话失效后自动重建
engine = create_engine(settings.database_url, pool_pre_ping=True)

# expire_on_commit=False：commit 后 ORM 对象仍可安全读取属性（API 序列化友好）
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：为单个请求提供会话，请求结束自动关闭。"""
    with SessionLocal() as session:
        yield session
