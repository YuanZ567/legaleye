"""M1-5 验收测试：敏感模式原文不落盘。

核心验证（PRD 第 6 章）：
- 敏感模式上传：不调用 MinIO 保存原文，库中 raw_text/minio_object_key 均为 NULL，仅存指纹；
- 默认模式上传：调用 MinIO 保存原文，minio_object_key 非空。
用 monkeypatch mock 掉 storage 函数（隔离真实 MinIO）。
"""

from collections.abc import Generator

import pytest
from app.core.db import get_db
from app.main import create_app
from app.models import SQLModel
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client_with_db() -> Generator[tuple[TestClient, sessionmaker], None, None]:
    """应用 + 内存 SQLite 会话（返回 TestClient 与共享的 sessionmaker 供查库）。"""
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
        yield c, TestingSession
    SQLModel.metadata.drop_all(engine)


def _make_pdf() -> bytes:
    import pymupdf

    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Privacy Policy Test Text")
    data = doc.tobytes()
    doc.close()
    return data


def _upload(client: TestClient, sensitive: bool):
    data = {"docType": "privacyPolicy"}
    if sensitive:
        data["sensitiveMode"] = "true"
    return client.post(
        "/documents",
        files={"file": ("policy.pdf", _make_pdf(), "application/pdf")},
        data=data,
    )


def _last_document(TestingSession) -> object:
    """从测试共享会话读取最新一条 Document。"""
    from app.models import Document

    with TestingSession() as session:
        return session.query(Document).order_by(Document.created_at.desc()).first()


def test_sensitive_mode_no_raw_persist(client_with_db, monkeypatch):
    """敏感模式：不调用 MinIO 保存原文；raw_text/minio_object_key 为 NULL，仅存指纹。"""
    client, TestingSession = client_with_db
    from app.services import document_service

    calls: list[tuple[str, str]] = []

    def fake_save(file_bytes: bytes, object_key: str) -> None:
        calls.append((object_key, len(file_bytes)))

    monkeypatch.setattr(document_service, "save_document_raw", fake_save)

    resp = _upload(client, sensitive=True)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["sensitiveMode"] is True

    # 敏感模式：不得调用 MinIO 保存原文
    assert calls == [], "敏感模式不应写入任何 MinIO 对象"

    doc = _last_document(TestingSession)
    assert doc is not None
    assert doc.sensitive_mode is True
    assert doc.raw_text is None  # 原文不落库（核心断言）
    assert doc.minio_object_key is None  # 原文对象不落盘
    assert doc.text_fingerprint is not None  # 仅存指纹摘要


def test_normal_mode_raw_persist(client_with_db, monkeypatch):
    """默认模式：调用 MinIO 保存原文，minio_object_key 非空，raw_text 落库。"""
    client, TestingSession = client_with_db
    from app.services import document_service

    calls: list[tuple[str, str]] = []

    def fake_save(file_bytes: bytes, object_key: str) -> None:
        calls.append((object_key, len(file_bytes)))

    monkeypatch.setattr(document_service, "save_document_raw", fake_save)

    resp = _upload(client, sensitive=False)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["sensitiveMode"] is False

    # 默认模式：应调用 MinIO 保存原文（1 次）
    assert len(calls) == 1
    assert calls[0][1] > 0

    doc = _last_document(TestingSession)
    assert doc is not None
    assert doc.raw_text is not None  # 原文落库
    assert doc.minio_object_key is not None  # 对象 key 已记录
    assert doc.minio_object_key.startswith("raw-docs/")
