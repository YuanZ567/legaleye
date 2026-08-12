"""M1-2 验收测试：上传 API 校验（格式/大小/页数 → 400）与成功落库。

使用 FastAPI TestClient + 内存 SQLite 覆盖 get_db 依赖，不触碰真实 PG。
"""

from collections.abc import Generator

import pytest
from app.core.constants import MAX_FILE_SIZE_BYTES, MAX_PDF_PAGES
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


def _make_pdf(page_count: int) -> bytes:
    """用 PyMuPDF 生成指定页数的文字版 PDF 字节流（英文避免默认字体不支持中文）。"""
    import pymupdf

    doc = pymupdf.open()
    for _ in range(page_count):
        page = doc.new_page()
        page.insert_text((72, 72), "Privacy Policy Test Text")
    data = doc.tobytes()
    doc.close()
    return data


# ── 成功路径 ──


def test_upload_pdf_success(client: TestClient):
    """文字版 PDF 上传成功并解析全文，返回契约字段。"""
    resp = client.post(
        "/documents",
        files={"file": ("policy.pdf", _make_pdf(2), "application/pdf")},
        data={"docType": "privacyPolicy"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["filename"] == "policy.pdf"
    assert body["docType"] == "privacyPolicy"
    assert body["sensitiveMode"] is False
    assert body["charCount"] > 0  # M1-4 已接入全文解析
    assert "Privacy Policy Test Text" in (body["textPreview"] or "")


# ── 异常路径（E1）──


def test_upload_unsupported_format_400(client: TestClient):
    """非支持格式（.txt）→ 400。"""
    resp = client.post(
        "/documents",
        files={"file": ("note.txt", b"hello", "text/plain")},
        data={"docType": "privacyPolicy"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "unsupported_format"
    assert "PDF" in resp.json()["error"]["message"]


def test_upload_too_large_400(client: TestClient):
    """超过 20MB → 400。"""
    big_bytes = b"x" * (MAX_FILE_SIZE_BYTES + 1)
    resp = client.post(
        "/documents",
        files={"file": ("big.pdf", big_bytes, "application/pdf")},
        data={"docType": "privacyPolicy"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "file_too_large"
    assert "20MB" in resp.json()["error"]["message"]


def test_upload_too_many_pages_400(client: TestClient):
    """PDF 超过 200 页 → 400。"""
    pdf = _make_pdf(MAX_PDF_PAGES + 1)
    resp = client.post(
        "/documents",
        files={"file": ("long.pdf", pdf, "application/pdf")},
        data={"docType": "privacyPolicy"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "too_many_pages"


def test_upload_missing_doc_type_400(client: TestClient):
    """未选择 docType 且文件名无法推断 → 400 提示手动选择。"""
    resp = client.post(
        "/documents",
        files={"file": ("random123.pdf", _make_pdf(1), "application/pdf")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "doc_type_required"


def test_upload_invalid_doc_type_400(client: TestClient):
    """非法 docType 值 → 400。"""
    resp = client.post(
        "/documents",
        files={"file": ("policy.pdf", _make_pdf(1), "application/pdf")},
        data={"docType": "notAType"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_doc_type"
