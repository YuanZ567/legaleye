"""Documents 业务服务：上传校验 + 落库（PRD F3）。

分层纪律（ARCHITECTURE 5.1）：
- 本模块是业务编排层，API 层只调用这里、不写业务逻辑；
- 校验失败抛 `ValidationError`（业务层禁止裸抛 HTTPException）；
- 查询/写入通过本服务内的 repository 逻辑集中完成，禁止散落原生 SQL。
"""

import asyncio
import hashlib
import uuid
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.constants import (
    MAX_FILE_SIZE_BYTES,
    MAX_PDF_PAGES,
    SUPPORTED_EXTENSIONS,
    TEXT_PREVIEW_LENGTH,
    URL_ALLOWED_SCHEMES,
    URL_FETCH_BACKOFF_SECONDS,
    URL_FETCH_MAX_RETRIES,
    URL_FETCH_TIMEOUT_SECONDS,
)
from app.core.enums import DocType
from app.core.exceptions import ValidationError
from app.models import Document
from app.utils.parsers import count_pdf_pages, get_file_extension, html_to_text, is_pdf


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


def _persist_document(
    *,
    db: Session,
    filename: str,
    doc_type: DocType,
    sensitive_mode: bool,
    user_id: uuid.UUID | None,
    raw_text: str | None,
    fingerprint_source: bytes | str,
) -> Document:
    """公共落库逻辑：敏感模式原文绝不持久化。

    :param raw_text: 解析后的纯文本；敏感模式下传入 None（原文不落库）。
    :param fingerprint_source: 指纹计算来源（文件字节或 URL 抓取文本）。
    """
    source_bytes = (
        fingerprint_source
        if isinstance(fingerprint_source, bytes)
        else fingerprint_source.encode("utf-8")
    )
    text_fingerprint = hashlib.sha256(source_bytes).hexdigest()

    # 敏感模式：仅存指纹摘要；否则存解析文本 + 前 500 字预览
    stored_raw = None if sensitive_mode else raw_text
    char_count = len(raw_text) if raw_text else 0
    text_preview = raw_text[:TEXT_PREVIEW_LENGTH] if raw_text else None

    doc = Document(
        user_id=user_id,
        filename=filename,
        doc_type=doc_type,
        sensitive_mode=sensitive_mode,
        raw_text=stored_raw,
        text_fingerprint=text_fingerprint,
        char_count=char_count,
        text_preview=text_preview,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


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
    return _persist_document(
        db=db,
        filename=filename,
        doc_type=doc_type,
        sensitive_mode=sensitive_mode,
        user_id=user_id,
        raw_text=None,  # M1-4 接入全文解析后回填
        fingerprint_source=file_bytes,
    )


async def _fetch_url_with_retry(url: str, *, transport: Any | None = None) -> str:
    """抓取 URL 内容，失败重试 1 次（指数退避），仍失败抛 ValidationError（E3）。

    返回抓取到的 HTML 字符串。超时 10s（httpx.Timeout）。

    :param transport: 可选的 httpx.AsyncBaseTransport（测试注入 MockTransport）。
    """
    import httpx

    last_error: Exception | None = None
    for attempt in range(URL_FETCH_MAX_RETRIES + 1):  # 初次 + 重试 N 次
        try:
            client_kwargs: dict[str, Any] = {
                "timeout": httpx.Timeout(URL_FETCH_TIMEOUT_SECONDS),
                "follow_redirects": True,
            }
            if transport is not None:
                client_kwargs["transport"] = transport
            async with httpx.AsyncClient(**client_kwargs) as client:
                resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:  # 网络/超时/非 2xx 均重试
            last_error = exc
            if attempt < URL_FETCH_MAX_RETRIES:
                # 指数退避：重试前等待
                await asyncio.sleep(URL_FETCH_BACKOFF_SECONDS)
    raise ValidationError(
        f"URL 抓取失败：{url}（{last_error}），请检查链接后重试",
        code="url_fetch_failed",
    )


async def create_document_from_url(
    *,
    db: Session,
    url: str,
    doc_type: DocType,
    user_id: uuid.UUID | None,
    transport: Any | None = None,
) -> Document:
    """URL 解析用例：校验协议 → 抓取（重试 1 次）→ html 转文本 → 落库（PRD F3/E3）。"""
    parsed = urlparse(url)
    if parsed.scheme not in URL_ALLOWED_SCHEMES or not parsed.netloc:
        raise ValidationError("URL 无效，仅支持 http/https 链接", code="invalid_url")

    html = await _fetch_url_with_retry(url, transport=transport)
    text = html_to_text(html)
    if not text:
        raise ValidationError("URL 内容为空或无法解析", code="parse_failed")

    # 用域名 + 路径作为文件名标识，便于任务列表识别来源
    filename = f"{parsed.netloc}{parsed.path or '/'}"
    return _persist_document(
        db=db,
        filename=filename,
        doc_type=doc_type,
        sensitive_mode=False,  # URL 内容为公开页面，按默认处理
        user_id=user_id,
        raw_text=text,
        fingerprint_source=text,
    )
