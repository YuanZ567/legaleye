"""全局业务常量（对齐 DATA_CONTRACT 3.2 / PRD F3）。"""

# 文件上传限制（PRD F3、DATA_CONTRACT 3.2）
MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024  # ≤20MB
MAX_PDF_PAGES: int = 200  # ≤200 页（仅 PDF 校验）

# 文本预览长度（DATA_CONTRACT 4.3：textPreview 前 500 字）
TEXT_PREVIEW_LENGTH: int = 500

# 支持的上传扩展名 → DocType（格式清单，用于 E1 校验）
SUPPORTED_EXTENSIONS: set[str] = {".pdf", ".docx"}

# URL 解析（PRD F3 / E3）：超时 10s，失败重试 1 次（指数退避）
URL_FETCH_TIMEOUT_SECONDS: float = 10.0
URL_FETCH_MAX_RETRIES: int = 1
URL_FETCH_BACKOFF_SECONDS: float = 1.0

# 允许的 URL 协议（E3：仅 http/https）
URL_ALLOWED_SCHEMES: tuple[str, ...] = ("http", "https")
