"""Documents 上传路由（薄层：仅参数校验 + 调 services）。

契约：POST /documents（multipart: file, docType, sensitiveMode?）→ {data: Document}
对齐 DATA_CONTRACT 4.3 / PRD F3。
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import DocType
from app.core.exceptions import ValidationError
from app.schemas.document import DocumentOut, UrlDocumentIn
from app.services.document_service import (
    create_document_from_upload,
    create_document_from_url,
)
from app.utils.parsers import infer_doc_type_from_filename

router = APIRouter(prefix="/documents", tags=["documents"])


def _parse_doc_type(value: str | None) -> DocType | None:
    """解析 docType 表单值；无效值抛 ValidationError（走 400）。"""
    if value is None or value == "":
        return None
    try:
        return DocType(value)
    except ValueError:
        raise ValidationError(
            f"无效的文档类型：{value}，可选值为 {[e.value for e in DocType]}",
            code="invalid_doc_type",
        ) from None


@router.post("")
async def upload_document(
    file: UploadFile = File(...),  # noqa: B008 (FastAPI 注入)
    doc_type: str | None = Form(default=None, alias="docType"),
    sensitive_mode: bool = Form(default=False, alias="sensitiveMode"),
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """上传合规文档并落库（PRD F3）。"""
    filename = file.filename or ""
    file_bytes = await file.read()

    # docType 未选择时按文件名启发式推断（PRD F3）；推断失败提示手动选择
    parsed_type = _parse_doc_type(doc_type)
    if parsed_type is None:
        parsed_type = infer_doc_type_from_filename(filename)
    if parsed_type is None:
        raise ValidationError(
            "无法自动识别文档类型，请手动选择（privacyPolicy / userAgreement / dpa / scc）",
            code="doc_type_required",
        )

    document = create_document_from_upload(
        db=db,
        filename=filename,
        file_bytes=file_bytes,
        doc_type=parsed_type,
        sensitive_mode=sensitive_mode,
        user_id=None,  # M8 接入 auth 后注入当前用户
    )
    return {
        "data": DocumentOut.model_validate(document, from_attributes=True).model_dump(by_alias=True)
    }


@router.post("/from-url")
async def upload_document_from_url(
    payload: UrlDocumentIn,
    db: Session = Depends(get_db),  # noqa: B008 (FastAPI 注入)
) -> dict:
    """从 URL 抓取并解析文档（PRD F3 / E3：10s 超时 + 重试 1 次）。"""
    document = await create_document_from_url(
        db=db,
        url=payload.url,
        doc_type=payload.doc_type,
        user_id=None,  # M8 接入 auth 后注入当前用户
    )
    return {
        "data": DocumentOut.model_validate(document, from_attributes=True).model_dump(by_alias=True)
    }
