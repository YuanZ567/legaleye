"""应用配置：全部来自环境变量（.env），禁止硬编码密钥。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """LegalEye 全局配置。

    读取优先级：环境变量 > .env 文件（backend/.env 或 ../infra/.env）。
    """

    model_config = SettingsConfigDict(
        # 读取顺序（后者优先级更高）：基础设施默认 < 本地开发覆盖。
        # 容器内由 compose env_file 注入环境变量（优先于所有 .env 文件），不受此顺序影响。
        env_file=("../infra/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_env: str = "development"
    log_level: str = "INFO"
    # JWT 签名密钥（生产必须从环境变量设置强随机值）
    jwt_secret: str = "legaleye-dev-jwt-secret-change-me"

    # 数据 / 队列
    database_url: str = (
        "postgresql+psycopg://legaleye:legaleye_dev_password@localhost:5432/legaleye"
    )
    redis_url: str = "redis://localhost:6379/0"

    # MinIO 文件存储（.env 覆盖；本地直连用 localhost:9000）
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "legaleye_minio"
    minio_root_password: str = "legaleye_minio_password"
    minio_bucket: str = "legaleye-docs"

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
    # demo 免 Key 用户每日限流（PRD 定案：3 次/日；配 Key 用户无限次）
    demo_daily_limit: int = 3

    # Embedding（M2-5 语义检索用；百炼 OpenAI 兼容接口，Key 从 OPENAI_API_KEY 读取）
    openai_api_key: str = ""  # 对应环境变量 OPENAI_API_KEY（百炼 DashScope 兼容模式）
    bailian_embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_embedding_model: str = "text-embedding-v1"  # 1536 维，与 LawBaseline.embedding 对齐
    embedding_dimension: int = 1536

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
