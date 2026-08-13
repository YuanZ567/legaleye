"""M4-6 验收测试：降级容错专项（超时重试 2 次 / 失败降级待补 / 10 分钟熔断）。

- factory 调用失败重试 2 次后成功；
- factory 重试后仍失败 → LLMError（交给上层降级）；
- 六维节点 LLM 失败 → 降级"待补 + needsHumanReview"（任务不中断）；
- Celery 任务总熔断 10 分钟（600s）。
"""

from collections.abc import Generator

import pytest
from app.core.enums import Provider
from app.core.exceptions import LLMError
from app.core.security import encrypt_secret
from app.llm import factory
from app.models import SQLModel
from app.models.model_config import ModelConfig
from sqlalchemy import create_engine
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
        session.add(
            ModelConfig(
                provider=Provider.BAILIAN,
                api_key_encrypted=encrypt_secret("sk-test"),
                model="qwen-plus",
                is_active=True,
            )
        )
        session.commit()
        yield session
    SQLModel.metadata.drop_all(engine)


def test_factory_retries_then_succeeds(db: Session, monkeypatch):
    """factory 调用失败重试 2 次后成功。"""
    attempts = {"n": 0}

    def flaky_completion(client, model, messages):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError("timeout")
        return {"text": "成功回复", "input_tokens": 10, "output_tokens": 5, "latency_ms": 100}

    monkeypatch.setattr(factory, "_openai_completion", flaky_completion)
    text = factory.chat_completion(
        db=db,
        provider=Provider.BAILIAN,
        model=None,
        messages=[{"role": "user", "content": "hi"}],
    )
    assert text == "成功回复"
    assert attempts["n"] == 3  # 初次 + 重试 2 次


def test_factory_retries_exhausted_raises(db: Session, monkeypatch):
    """factory 重试后仍失败 → LLMError（上层可降级）。"""

    def always_fail(client, model, messages):  # noqa: ARG001
        raise ConnectionError("persistent failure")

    monkeypatch.setattr(factory, "_openai_completion", always_fail)
    with pytest.raises(LLMError):
        factory.chat_completion(
            db=db,
            provider=Provider.BAILIAN,
            model=None,
            messages=[{"role": "user", "content": "hi"}],
        )


def test_dimension_agent_degrades_on_llm_error():
    """六维节点 LLM 失败 → 降级待补 + needsHumanReview（任务不中断）。"""
    import asyncio

    from app.agents.dimension_agent import build_dimension_node

    async def raise_llm(**kwargs):
        raise LLMError("LLM 调用重试 2 次仍失败", code="llm_failed")

    node = build_dimension_node("d1", raise_llm)
    result = asyncio.run(
        node({"task_id": "t", "document_text": "d", "retrieval": "", "graph_summary": ""})
    )
    finding = result["findings"][0]
    assert finding["clauseRef"] == "待补"
    assert finding["needsHumanReview"] is True


def test_task_total_circuit_breaker():
    """Celery 任务总熔断 10 分钟（600s）。"""
    from app.tasks.celery_app import celery_app

    assert celery_app.conf.task_time_limit == 600
    assert celery_app.conf.task_soft_time_limit == 570
