"""全局业务常量（对齐 DATA_CONTRACT 3.2 / PRD F3）。"""

# 文件上传限制（PRD F3、DATA_CONTRACT 3.2）
MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024  # ≤20MB
MAX_PDF_PAGES: int = 200  # ≤200 页（仅 PDF 校验）

# 文本预览长度（DATA_CONTRACT 4.3：textPreview 前 500 字）
TEXT_PREVIEW_LENGTH: int = 500

# 支持的上传扩展名 → DocType（格式清单，用于 E1 校验）
SUPPORTED_EXTENSIONS: set[str] = {".pdf", ".docx"}
