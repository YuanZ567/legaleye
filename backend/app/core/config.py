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

    # 法规库基线版本（报告锁存当时的法规版本，M9-1 从 config 读，禁止硬编码）
    laws_baseline_version: str = "laws-v1.0-20260811"

    # Embedding（M2-5 语义检索用；百炼 OpenAI 兼容接口，Key 从 OPENAI_API_KEY 读取）
    openai_api_key: str = ""  # 对应环境变量 OPENAI_API_KEY（百炼 DashScope 兼容模式）
    bailian_embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_embedding_model: str = "text-embedding-v1"  # 1536 维，与 LawBaseline.embedding 对齐
    embedding_dimension: int = 1536

    # 任务（Celery / 熔断）
    celery_worker_concurrency: int = 2
    task_timeout_seconds: int = 600
    max_task_tokens: int = 400000

    # OAuth（M9-6：GitHub 全链路 + QQ 接口就绪；凭据只来自 .env，禁硬编码）
    # 回调地址基址（后端完成授权后 302 跳回前端 SPA，如 http://localhost:5173）
    oauth_redirect_base: str = "http://localhost:5173"
    # 后端对外可访问的基址（GitHub/QQ 回调 URL 指向此处，如 http://localhost:8000）
    api_base_url: str = "http://localhost:8000"
    # GitHub OAuth（本地联调可配）
    github_client_id: str = ""
    github_client_secret: str = ""
    # QQ OAuth（凭据留空 = 接口就绪但未开通，authorize 返回 503）
    qq_app_id: str = ""
    qq_app_key: str = ""
    # OAuth state 有效期（防 CSRF，Redis TTL，秒）
    oauth_state_ttl_seconds: int = 300

    # 可观测
    sentry_dsn: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        """解析逗号分隔的 CORS 来源为列表。"""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
