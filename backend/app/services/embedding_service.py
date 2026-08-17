"""Embedding 生成服务（M9-7）：单条文本向量化，供知识库添加法条等 API 共用。

纪律（ARCHITECTURE 6.1 / M9-7 红线 2）：
- 禁止裸调 LLM，统一经 llm/embeddings 工厂；
- embedding 生成失败 → 明确抛错（法条入库必须有向量，不静默降级）；
- 脚本入库走 retrieval.embed_law_baseline（批量回填），本服务提供单条生成，
  二者共用同一 provider 工厂，避免逻辑复制。
"""

from app.core.exceptions import DomainError
from app.llm.embeddings import get_embedding_provider


def embed_text(text: str) -> list[float]:
    """把单条文本向量化（百炼 text-embedding-v1，1536 维）。

    :raises DomainError: embedding 生成失败（不静默降级）。
    """
    try:
        provider = get_embedding_provider()
        return provider.embed([text])[0]
    except Exception as exc:  # noqa: BLE001 - 统一包装为可读错误
        raise DomainError(
            f"Embedding 生成失败：{exc}", code="embedding_failed", status_code=500
        ) from exc
