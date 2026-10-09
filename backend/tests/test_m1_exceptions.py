"""M1-6 收尾验收：异常用例（E1-E3）专项覆盖。

显式对照 DATA_CONTRACT 异常语义：
- E1 输入/格式校验失败 → 400；
- E2 扫描版 PDF（无文字层）→ 400 明确提示；
- E3 URL 抓取失败（重试后仍失败）→ 400。

conftest autouse 已禁用真实 MinIO，测试仅依赖内存 SQLite + MockTransport。
"""

from collections.abc import Generator

import httpx
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


def _make_pdf() -> bytes:
    import pymupdf

    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Privacy Policy Test Text")
    data = doc.tobytes()
    doc.close()
    return data


# ── E1：输入/格式校验失败 → 400 ──


def test_e1_corrupt_pdf_400(client: TestClient):
    """损坏/空 PDF 无法解析 → 400 parse_failed。"""
    resp = client.post(
        "/documents",
        files={"file": ("broken.pdf", b"not a real pdf", "application/pdf")},
        data={"docType": "privacyPolicy"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "parse_failed"


def test_e1_invalid_doc_type_400(client: TestClient):
    """非法 docType 值 → 400 invalid_doc_type。"""
    resp = client.post(
        "/documents",
        files={"file": ("policy.pdf", _make_pdf(), "application/pdf")},
        data={"docType": "notAType"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_doc_type"


def test_e1_unsupported_format_400(client: TestClient):
    """非支持格式（.exe）→ 400 unsupported_format。（.txt 已支持，见 document_service）"""
    resp = client.post(
        "/documents",
        files={"file": ("note.exe", b"hello", "application/octet-stream")},
        data={"docType": "privacyPolicy"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "unsupported_format"


# ── E2：扫描版 PDF → 400 ──


def test_e2_scanned_pdf_400(client: TestClient):
    """无文字层 PDF（扫描版）→ 400 scanned_pdf，明确提示不支持 OCR。"""
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()  # 空白页，无文字
    data = doc.tobytes()
    doc.close()

    resp = client.post(
        "/documents",
        files={"file": ("scan.pdf", data, "application/pdf")},
        data={"docType": "privacyPolicy"},
    )
    assert resp.status_code == 400
    body = resp.json()["error"]
    assert body["code"] == "scanned_pdf"
    assert "OCR" in body["message"] or "文字层" in body["message"]


# ── E3：URL 抓取失败（重试后仍失败）→ 400 ──


async def test_e3_url_fetch_fails_after_retry(db_session: Session):
    """URL 持续失败 → 400 url_fetch_failed，且重试 1 次（共 2 次尝试）。"""
    from app.core.enums import DocType
    from app.core.exceptions import ValidationError
    from app.services.document_service import create_document_from_url

    call_count = 0

    def fail_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("connection refused")

    with pytest.raises(ValidationError) as exc:
        await create_document_from_url(
            db=db_session,
            url="https://example.com/down",
            doc_type=DocType.SCC,
            user_id=None,
            transport=httpx.MockTransport(fail_handler),
        )
    assert exc.value.code == "url_fetch_failed"
    assert call_count == 2  # 初次 + 重试 1 次


async def test_e3_url_http_error_after_retry(db_session: Session):
    """URL 返回非 2xx（如 404）重试后仍失败 → 400 url_fetch_failed。"""
    from app.core.enums import DocType
    from app.core.exceptions import ValidationError
    from app.services.document_service import create_document_from_url

    call_count = 0

    def not_found_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(404)

    with pytest.raises(ValidationError) as exc:
        await create_document_from_url(
            db=db_session,
            url="https://example.com/missing",
            doc_type=DocType.DPA,
            user_id=None,
            transport=httpx.MockTransport(not_found_handler),
        )
    assert exc.value.code == "url_fetch_failed"
    assert call_count == 2


# ── 独立 db_session fixture（供 async 服务层测试）──


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """内存 SQLite 会话（服务层 async 测试用）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.models import SQLModel

    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestingSession() as session:
        yield session
    SQLModel.metadata.drop_all(engine)
