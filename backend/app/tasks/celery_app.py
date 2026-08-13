"""Celery 应用实例（M4-3 骨架）。

broker/backend 用 Redis；任务注册在 tasks 包内。
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "legaleye",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.review_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 降级容错（ARCHITECTURE 6.4）：任务总熔断 10 分钟（单 LLM 调用 60s 超时由 factory 层控制）
    task_time_limit=600,
    task_soft_time_limit=570,
    task_acks_late=True,
)
