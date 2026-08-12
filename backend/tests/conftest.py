"""全局测试配置：自动禁用真实 MinIO 依赖。

上传用例默认模式会写 MinIO（ARCHITECTURE 红线：原文对象落盘）。
为避免单测依赖外部 MinIO 服务，此处 autouse 将所有 storage 写操作替换为 no-op，
并让 build_object_key 返回稳定 key。M1-5 敏感模式测试通过显式重新 monkeypatch
`save_document_raw` 来验证"敏感模式不落盘 / 默认模式落盘"。
"""

import pytest


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
