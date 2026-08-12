"""M1-3 验收测试：URL 解析（from-url）成功落库 + E3 异常（重试/无效/空内容）。

服务层单测通过 httpx.MockTransport 注入（不碰真实网络）；
API 层测试通过 monkeypatch 服务函数隔离网络。
"""

import uuid
from collections.abc import Generator

import httpx
import pytest
from app.core.db import get_db
from app.main import create_app
from app.models import SQLModel
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ── 服务层单测（MockTransport 注入）──


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """内存 SQLite 会话。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestingSession() as session:
        yield session
    SQLModel.metadata.drop_all(engine)


async def test_from_url_success(db_session: Session):
    """合法 URL 成功抓取并落库，返回契约字段。"""
    from app.core.enums import DocType
    from app.services.document_service import create_document_from_url

    html_body = "<html><body><p>隐私政策：收集姓名</p></body></html>"
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html_body))
    doc = await create_document_from_url(
        db=db_session,
        url="https://example.com/policy",
        doc_type=DocType.PRIVACY_POLICY,
        user_id=None,
        transport=transport,
    )
    assert doc.filename == "example.com/policy"
    assert doc.doc_type == DocType.PRIVACY_POLICY
    assert doc.char_count > 0
    assert "收集姓名" in (doc.raw_text or "")
    assert (doc.text_preview or "").startswith("隐私政策")


async def test_from_url_invalid_scheme(db_session: Session):
    """非 http/https 协议 → ValidationError（E3 invalid_url）。"""
    from app.core.enums import DocType
    from app.core.exceptions import ValidationError
    from app.services.document_service import create_document_from_url

    with pytest.raises(ValidationError) as exc:
        await create_document_from_url(
            db=db_session,
            url="ftp://example.com/a",
            doc_type=DocType.DPA,
            user_id=None,
        )
    assert exc.value.code == "invalid_url"


async def test_from_url_fetch_failed_after_retry(db_session: Session):
    """抓取失败重试 1 次后仍失败 → ValidationError（E3 url_fetch_failed）。"""
    from app.core.enums import DocType
    from app.core.exceptions import ValidationError
    from app.services.document_service import create_document_from_url

    call_count = 0

    def fail_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(fail_handler)
    with pytest.raises(ValidationError) as exc:
        await create_document_from_url(
            db=db_session,
            url="https://example.com/down",
            doc_type=DocType.SCC,
            user_id=None,
            transport=transport,
        )
    assert exc.value.code == "url_fetch_failed"
    assert call_count == 2  # 初次 + 重试 1 次


async def test_from_url_empty_content(db_session: Session):
    """抓取成功但内容为空 → ValidationError（E3 parse_failed）。"""
    from app.core.enums import DocType
    from app.core.exceptions import ValidationError
    from app.services.document_service import create_document_from_url

    transport = httpx.MockTransport(lambda req: httpx.Response(200, text="<script>x</script>"))
    with pytest.raises(ValidationError) as exc:
        await create_document_from_url(
            db=db_session,
            url="https://example.com/empty",
            doc_type=DocType.DPA,
            user_id=None,
            transport=transport,
        )
    assert exc.value.code == "parse_failed"


# ── API 层测试（monkeypatch 服务函数隔离网络）──


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """应用 + 内存 SQLite 会话。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


def _fake_document(doc_type: str = "privacyPolicy"):
    """构造一个 Document ORM 实例（用于 monkeypatch 服务返回）。"""
    from datetime import datetime

    from app.core.enums import DocType
    from app.models import Document

    return Document(
        id=uuid.uuid4(),
        filename="example.com/policy",
        doc_type=DocType(doc_type),
        sensitive_mode=False,
        raw_text="隐私政策正文",
        char_count=5,
        text_preview="隐私政策正文",
        text_fingerprint="f" * 64,
        created_at=datetime.now(),
    )


def test_api_from_url_success(client: TestClient, monkeypatch):
    """API：合法 URL → 200 + 契约字段。"""
    import app.api.documents as documents_api

    async def fake(*, db, url, doc_type, user_id, transport=None):  # noqa: ARG001
        return _fake_document()

    monkeypatch.setattr(documents_api, "create_document_from_url", fake)
    resp = client.post(
        "/documents/from-url",
        json={"url": "https://example.com/policy", "docType": "privacyPolicy"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["docType"] == "privacyPolicy"
    assert body["charCount"] == 5


def test_api_from_url_invalid_url_400(client: TestClient, monkeypatch):
    """API：非法 URL → 400。"""
    import app.api.documents as documents_api
    from app.core.exceptions import ValidationError

    async def fake(*, db, url, doc_type, user_id, transport=None):  # noqa: ARG001
        raise ValidationError("URL 无效，仅支持 http/https 链接", code="invalid_url")

    monkeypatch.setattr(documents_api, "create_document_from_url", fake)
    resp = client.post(
        "/documents/from-url",
        json={"url": "not-a-url", "docType": "dpa"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_url"
