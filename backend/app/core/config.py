"""应用配置：全部来自环境变量（.env），禁止硬编码密钥。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """LegalEye 全局配置。

    读取优先级：环境变量 > .env 文件（backend/.env 或 ../infra/.env）。
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../infra/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_env: str = "development"
    log_level: str = "INFO"

    # 数据 / 队列
    database_url: str = "postgresql+psycopg://legaleye:legaleye_dev_password@localhost:5432/legaleye"
    redis_url: str = "redis://localhost:6379/0"

    # 安全（必填，来自 .env）
    legaleye_secret_key: str = ""
    jwt_secret: str = ""
    jwt_access_expire_minutes: int = 120
    jwt_refresh_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:5173"

    # LLM（M4 起使用；demo 免 Key 走系统默认百炼）
    bailian_api_key: str = ""
    bailian_model: str = "qwen-plus"
    demo_daily_limit: int = 5

    # 任务（Celery / 熔断）
    celery_worker_concurrency: int = 2
    task_timeout_seconds: int = 600
    max_task_tokens: int = 400000

    # 可观测
    sentry_dsn: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        """解析逗号分隔的 CORS 来源为列表。"""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
