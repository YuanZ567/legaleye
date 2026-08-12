"""M1-4 验收测试：上传文件全文解析（PDF/docx）+ 扫描版 PDF（E2）+ docType 文件名推断。

使用 FastAPI TestClient + 内存 SQLite 覆盖 get_db 依赖。
"""

import io
from collections.abc import Generator

import pytest
from app.core.db import get_db
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """应用 + 内存 SQLite 会话（隔离真实 PG）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.models import SQLModel

    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSession() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    SQLModel.metadata.drop_all(engine)


def _make_text_pdf(content: str = "Privacy Policy Test Text") -> bytes:
    """生成含文字层的 PDF（用英文避免 PyMuPDF 默认字体不支持中文）。"""
    import pymupdf

    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), content)
    data = doc.tobytes()
    doc.close()
    return data


def _make_scanned_pdf() -> bytes:
    """生成无文字层的扫描版 PDF（仅空白页）。"""
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()  # 空页，无文字
    data = doc.tobytes()
    doc.close()
    return data


def _make_docx(content: str = "数据处理协议：受托方为阿里云") -> bytes:
    """生成含文本的 .docx。"""
    import docx

    document = docx.Document()
    document.add_paragraph(content)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


# ── 成功路径：文本解析落库 ──


def test_upload_pdf_extracts_text(client: TestClient):
    """文字版 PDF 解析全文到 raw_text/text_preview/charCount。"""
    resp = client.post(
        "/documents",
        files={
            "file": (
                "policy.pdf",
                _make_text_pdf("Privacy Policy Test Text"),
                "application/pdf",
            )
        },
        data={"docType": "privacyPolicy"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["charCount"] > 0
    assert body["textPreview"] is not None
    assert "Privacy Policy Test Text" in body["textPreview"]


def test_upload_docx_extracts_text(client: TestClient):
    """docx 解析全文到 raw_text。"""
    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    resp = client.post(
        "/documents",
        files={"file": ("dpa.docx", _make_docx(), mime)},
        data={"docType": "dpa"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["charCount"] > 0
    assert "受托方" in (body["textPreview"] or "")


# ── E2：扫描版 PDF ──


def test_upload_scanned_pdf_400(client: TestClient):
    """扫描版 PDF（无文字层）→ 400（E2，明确提示不支持 OCR）。"""
    resp = client.post(
        "/documents",
        files={"file": ("scan.pdf", _make_scanned_pdf(), "application/pdf")},
        data={"docType": "privacyPolicy"},
    )
    assert resp.status_code == 400
    body = resp.json()["error"]
    assert body["code"] == "scanned_pdf"
    assert "OCR" in body["message"] or "文字层" in body["message"]


# ── docType 文件名启发式推断 ──


def test_upload_infer_doc_type_from_filename(client: TestClient):
    """未传 docType 时按文件名推断成功。"""
    resp = client.post(
        "/documents",
        files={"file": ("隐私政策.pdf", _make_text_pdf(), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["docType"] == "privacyPolicy"


def test_upload_infer_doc_type_fail_400(client: TestClient):
    """文件名无法推断 docType → 400（doc_type_required）。"""
    resp = client.post(
        "/documents",
        files={"file": ("random123.pdf", _make_text_pdf(), "application/pdf")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "doc_type_required"


# ── 敏感模式：原文不落库 ──


def test_upload_sensitive_mode_raw_text_not_persisted(client: TestClient):
    """敏感模式下 raw_text 不持久化，仅返回元数据。"""
    resp = client.post(
        "/documents",
        files={"file": ("policy.pdf", _make_text_pdf(), "application/pdf")},
        data={"docType": "privacyPolicy", "sensitiveMode": "true"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["sensitiveMode"] is True
