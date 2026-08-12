"""M1-1 验收测试：Document ORM 可建表/插入/查询；敏感模式原文不落库。

使用 SQLite 内存库验证模型层（与 PG 仅差异：native_enum 均已关闭）。
"""

import pytest
from app.core.enums import DocType
from app.models import Document, SQLModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def in_memory_db():
    """进程内 SQLite 引擎：建表 → 测试 → 清表。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


def test_doc_type_enum_values_match_contract():
    """DATA_CONTRACT 3.1：枚举值即 API 传输值（camelCase）。"""
    assert DocType.PRIVACY_POLICY.value == "privacyPolicy"
    assert DocType.USER_AGREEMENT.value == "userAgreement"
    assert DocType.DPA.value == "dpa"
    assert DocType.SCC.value == "scc"


def test_document_crud(in_memory_db):
    """默认模式：元数据 + 原文均可持久化并回读。"""
    with Session(in_memory_db) as session:
        doc = Document(
            filename="privacy_policy.pdf",
            doc_type=DocType.PRIVACY_POLICY,
            char_count=1234,
            text_preview="我们收集以下信息…",
            raw_text="这是完整原文。",
            sensitive_mode=False,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

        loaded = session.get(Document, doc.id)
        assert loaded is not None
        assert loaded.filename == "privacy_policy.pdf"
        assert loaded.doc_type == DocType.PRIVACY_POLICY
        assert loaded.char_count == 1234
        assert loaded.text_preview == "我们收集以下信息…"
        assert loaded.raw_text == "这是完整原文。"
        assert loaded.sensitive_mode is False
        assert loaded.created_at is not None  # server_default now() 已落库


def test_sensitive_mode_raw_text_not_persisted(in_memory_db):
    """敏感模式：raw_text 必须为 NULL，仅存 text_fingerprint 摘要（PRD 第 6 章）。"""
    with Session(in_memory_db) as session:
        doc = Document(
            filename="sensitive_dpa.docx",
            doc_type=DocType.DPA,
            sensitive_mode=True,
            raw_text=None,  # 敏感模式纪律：原文不入库
            text_fingerprint="a" * 64,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

        loaded = session.get(Document, doc.id)
        assert loaded.sensitive_mode is True
        assert loaded.raw_text is None
        assert loaded.text_fingerprint == "a" * 64
        assert loaded.char_count == 0  # 未解析时的默认值
