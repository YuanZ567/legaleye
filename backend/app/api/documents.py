"""Documents 上传路由（薄层：仅参数校验 + 调 services）。

契约：POST /documents（multipart: file, docType, sensitiveMode?）→ {data: Document}
对齐 DATA_CONTRACT 4.3 / PRD F3。
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import DocType
from app.core.exceptions import ValidationError
from app.schemas.document import DocumentOut
from app.services.document_service import create_document_from_upload

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
    # 校验必填：docType 未选择时由前端/后端启发式推断（推断失败提示手动选择）
    parsed_type = _parse_doc_type(doc_type)
    if parsed_type is None:
        # M1-4 接入文件名启发式推断；当前要求显式选择
        raise ValidationError(
            "请选择文档类型（privacyPolicy / userAgreement / dpa / scc）",
            code="doc_type_required",
        )

    file_bytes = await file.read()
    document = create_document_from_upload(
        db=db,
        filename=file.filename or "",
        file_bytes=file_bytes,
        doc_type=parsed_type,
        sensitive_mode=sensitive_mode,
        user_id=None,  # M8 接入 auth 后注入当前用户
    )
    return {
        "data": DocumentOut.model_validate(document, from_attributes=True).model_dump(by_alias=True)
    }
