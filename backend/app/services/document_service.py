"""Documents 业务服务：上传校验 + 落库（PRD F3）。

分层纪律（ARCHITECTURE 5.1）：
- 本模块是业务编排层，API 层只调用这里、不写业务逻辑；
- 校验失败抛 `ValidationError`（业务层禁止裸抛 HTTPException）；
- 查询/写入通过本服务内的 repository 逻辑集中完成，禁止散落原生 SQL。
"""

import hashlib
import uuid

from sqlalchemy.orm import Session

from app.core.constants import (
    MAX_FILE_SIZE_BYTES,
    MAX_PDF_PAGES,
    SUPPORTED_EXTENSIONS,
)
from app.core.enums import DocType
from app.core.exceptions import ValidationError
from app.models import Document
from app.utils.parsers import count_pdf_pages, get_file_extension, is_pdf


def _validate_upload(filename: str, file_bytes: bytes) -> None:
    """格式 + 大小 + 页数校验，违规抛 ValidationError（E1 语义）。"""
    # E1：非支持格式
    ext = get_file_extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValidationError(
            "不支持的文件格式，请上传 PDF 或 Word（.pdf / .docx）",
            code="unsupported_format",
        )

    # E1：文件过大（≤20MB）
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValidationError("文件过大（≤20MB），请压缩后重试", code="file_too_large")

    # E1：页数超过限制（仅 PDF，≤200 页）
    if is_pdf(filename):
        try:
            page_count = count_pdf_pages(file_bytes)
        except Exception:
            raise ValidationError(
                "文件内容为空或无法解析，请检查文件是否损坏", code="parse_failed"
            ) from None
        if page_count > MAX_PDF_PAGES:
            raise ValidationError("文件页数超过 200 页，请拆分为多份后上传", code="too_many_pages")


def create_document_from_upload(
    *,
    db: Session,
    filename: str,
    file_bytes: bytes,
    doc_type: DocType,
    sensitive_mode: bool,
    user_id: uuid.UUID | None,
) -> Document:
    """上传文档用例：校验 → 落库 → 返回 ORM 实体。

    注：文本全文提取（PyMuPDF/python-docx）在 M1-4 接入；
      当前仅校验并落库元数据，raw_text/text_preview 留待解析后回填。
    """
    _validate_upload(filename, file_bytes)

    doc = Document(
        user_id=user_id,
        filename=filename,
        doc_type=doc_type,
        sensitive_mode=sensitive_mode,
        # 敏感模式下原文绝不持久化；默认模式下也仅在解析后（M1-4）落库
        raw_text=None,
        text_fingerprint=hashlib.sha256(file_bytes).hexdigest(),
        char_count=0,
        text_preview=None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
