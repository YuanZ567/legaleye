"""M4-1 验收测试：LLM 工厂（四 provider 路由 + Fernet 解密 + LLMCallRecord 记账）。

- Fernet 加解密往返；
- 未配置 ModelConfig → LLMConfigError（不静默 fallback）；
- chat_completion 解密 Key + 记账（LLMCallRecord 写入 tokens/latency）；
- 四 provider 路由分发（monkeypatch 底层 completion）。
"""

import uuid
from collections.abc import Generator

import pytest
from app.core.enums import Provider
from app.core.exceptions import LLMError
from app.core.security import decrypt_secret, encrypt_secret
from app.llm import factory
from app.models import SQLModel
from app.models.model_config import LLMCallRecord, ModelConfig
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db() -> Generator[Session, None, None]:
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


def _seed_config(
    db: Session, provider: Provider = Provider.BAILIAN, key: str = "sk-test-12345"
) -> None:
    db.add(
        ModelConfig(
            provider=provider,
            api_key_encrypted=encrypt_secret(key),
            model="qwen-plus",
            is_active=True,
        )
    )
    db.commit()


# ── Fernet 加解密 ──


def test_fernet_roundtrip():
    """Fernet 加密/解密往返一致。"""
    secret = "sk-abcdef-12345"
    cipher = encrypt_secret(secret)
    assert cipher != secret
    assert decrypt_secret(cipher) == secret


def test_fernet_wrong_key_raises(monkeypatch):
    """密钥不匹配解密 → SecurityError（InvalidToken）。"""
    from types import SimpleNamespace

    from app.core import security
    from app.core.security import SecurityError
    from cryptography.fernet import Fernet

    good_key = Fernet.generate_key().decode("utf-8")
    # 用正常密钥加密
    monkeypatch.setattr(
        security, "get_settings", lambda: SimpleNamespace(legaleye_secret_key=good_key)
    )
    cipher = encrypt_secret("sk-x")
    # 切换到另一个密钥解密 → InvalidToken → SecurityError
    other_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr(
        security, "get_settings", lambda: SimpleNamespace(legaleye_secret_key=other_key)
    )
    with pytest.raises(SecurityError):
        decrypt_secret(cipher)


# ── 配置缺失 ──


def test_no_config_raises(db: Session):
    """未配置活跃模型 → LLMConfigError（不静默）。"""
    with pytest.raises(LLMError):
        factory.chat_completion(
            db=db,
            provider=Provider.BAILIAN,
            model=None,
            messages=[{"role": "user", "content": "hi"}],
        )


# ── chat_completion 路由 + 记账 ──


def test_chat_completion_records_call(db: Session, monkeypatch):
    """chat_completion 解密 Key + 记账（LLMCallRecord 写入 tokens）。"""
    _seed_config(db)
    captured = {}

    def fake_openai(client, model, messages):
        captured["model"] = model
        return {"text": "回复", "input_tokens": 120, "output_tokens": 30, "latency_ms": 500}

    monkeypatch.setattr(factory, "_openai_completion", fake_openai)

    text = factory.chat_completion(
        db=db,
        provider=Provider.BAILIAN,
        model=None,
        messages=[{"role": "user", "content": "分析"}],
        node="d1",
        task_id=uuid.uuid4(),
    )
    assert text == "回复"
    assert captured["model"] == "qwen-plus"

    record = db.scalar(select(LLMCallRecord))
    assert record is not None
    assert record.provider == Provider.BAILIAN
    assert record.input_tokens == 120
    assert record.output_tokens == 30
    assert record.latency_ms == 500
    assert record.node == "d1"


def test_provider_routing(monkeypatch):
    """四 provider 路由：bailian/deepseek/openai 走 OpenAI 兼容，anthropic 走 Anthropic。"""
    routed = []

    def fake_openai(client, model, messages):
        routed.append("openai")
        return {"text": "ok", "input_tokens": 0, "output_tokens": 0, "latency_ms": 1}

    def fake_anthropic(client, model, messages):
        routed.append("anthropic")
        return {"text": "ok", "input_tokens": 0, "output_tokens": 0, "latency_ms": 1}

    monkeypatch.setattr(factory, "_openai_completion", fake_openai)
    monkeypatch.setattr(factory, "_anthropic_completion", fake_anthropic)

    # 用内存 db 逐一测（构造临时 session）
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    for p, expect in [
        (Provider.BAILIAN, "openai"),
        (Provider.DEEPSEEK, "openai"),
        (Provider.OPENAI, "openai"),
        (Provider.ANTHROPIC, "anthropic"),
    ]:
        with TestingSession() as s:
            _seed_config(s, provider=p)
            factory.chat_completion(
                db=s,
                provider=p,
                model=None,
                messages=[{"role": "user", "content": "x"}],
            )
        assert routed[-1] == expect, f"{p} 应走 {expect}"

    SQLModel.metadata.drop_all(engine)
