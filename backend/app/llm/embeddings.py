"""Embedding 工厂（M2-5 语义检索用）。

分层纪律（ARCHITECTURE 6.1）：检索/分析层禁止裸调 LLM，统一经本工厂获取 Provider；
外部依赖（百炼 OpenAI 兼容接口）只在本模块出现。

设计：
- `EmbeddingProvider` 协议：embed(texts) -> list[list[float]]；
- `BailianOpenAIEmbeddings`：百炼 DashScope 兼容接口实现（Key 从 OPENAI_API_KEY 读取）；
- `get_embedding_provider()`：工厂，支持运行时注入（测试用 mock；CI 走 mock）。
"""

from typing import Protocol

from app.core.config import get_settings


class EmbeddingProvider(Protocol):
    """向量化协议：把文本批量转为 embedding 向量。"""

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class BailianOpenAIEmbeddings:
    """百炼 OpenAI 兼容 embedding 实现（text-embedding-v1，1536 维）。

    Key 从 config.openai_api_key 读取（环境变量 OPENAI_API_KEY）。
    """

    def __init__(self) -> None:
        from openai import OpenAI

        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("未配置 OPENAI_API_KEY（百炼 DashScope），无法生成 embedding。")
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.bailian_embedding_base_url,
        )
        self._model = settings.bailian_embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化；返回与输入等长的向量列表（维度对齐模型，如 1536）。"""
        resp = self._client.embeddings.create(model=self._model, input=texts)
        # 按输入顺序返回向量
        ordered = sorted(resp.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]


_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """获取全局 embedding Provider（支持测试注入覆盖 `_provider`）。"""
    global _provider
    if _provider is None:
        _provider = BailianOpenAIEmbeddings()
    return _provider


def set_embedding_provider(provider: EmbeddingProvider) -> None:
    """注入自定义 Provider（测试/CI 用 mock；生产不调用）。"""
    global _provider
    _provider = provider
