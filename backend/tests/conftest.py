"""全局测试配置：自动禁用真实 MinIO 依赖，并补齐 CI 缺失的环境变量。

上传用例默认模式会写 MinIO（ARCHITECTURE 红线：原文对象落盘）。
为避免单测依赖外部 MinIO 服务，此处 autouse 将所有 storage 写操作替换为 no-op，
并让 build_object_key 返回稳定 key。M1-5 敏感模式测试通过显式重新 monkeypatch
`save_document_raw` 来验证"敏感模式不落盘 / 默认模式落盘"。

环境变量：CI 没有 infra/.env，加密与 JWT 用例会因密钥为空而失败。
这里用 setdefault 只补缺省值（本地/容器已配置时不受影响），密钥为测试专用固定值。
"""

import os

import pytest

# 必须在 app.core.config 首次实例化前写入，否则 lru_cache 会缓存空密钥
os.environ.setdefault("LEGALEYE_SECRET_KEY", "zq4l0c9eR_5ghjK6RjqNjzToyf_uGIbHacMai6c1Xas=")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-not-for-production")


@pytest.fixture(autouse=True)
def _disable_minio(monkeypatch):
    """默认禁用真实 MinIO；M1-5 测试可覆盖此 monkeypatch。"""
    from app.services import document_service

    def noop_save(file_bytes: bytes, object_key: str) -> None:
        return None

    monkeypatch.setattr(document_service, "save_document_raw", noop_save)
    monkeypatch.setattr(
        document_service, "build_object_key", lambda filename: f"raw-docs/{filename}"
    )
