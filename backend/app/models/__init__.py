"""ORM 模型包：统一在此导出，alembic env 依赖本包注册全部表模型。"""

from sqlmodel import SQLModel

from app.models.document import Document

__all__ = ["Document", "SQLModel"]
