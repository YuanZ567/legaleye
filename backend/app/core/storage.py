"""MinIO 文件存储封装（ARCHITECTURE 红线：api 不直接写文件存储，统一走这里）。

职责：
- 提供全局 MinIO 客户端（lazy 单例）；
- bucket 存在性保障；
- 保存/列举"原始上传文件"对象。

敏感模式纪律（PRD 第 6 章）：敏感模式下不调用 save_document_raw，
仅依赖方（services）保证——本模块不承担业务判断，只提供能力。
"""

import io
import uuid
from functools import lru_cache

from minio import Minio

from app.core.config import get_settings

# 对象 key 前缀：所有原始文件对象统一放在该前缀下，便于列举/清理
OBJECT_PREFIX = "raw-docs"


@lru_cache
def get_minio_client() -> Minio:
    """获取全局 MinIO 客户端（lazy 单例）。"""
    settings = get_settings()
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=False,  # 本地开发走 http
    )
    return client


def ensure_bucket(client: Minio | None = None) -> None:
    """确保目标 bucket 存在（不存在则创建）。"""
    client = client or get_minio_client()
    bucket = get_settings().minio_bucket
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def build_object_key(filename: str) -> str:
    """生成 MinIO 对象 key：`raw-docs/{uuid}{ext}`，按上传文件唯一化。"""
    from pathlib import Path

    ext = Path(filename).suffix.lower()
    return f"{OBJECT_PREFIX}/{uuid.uuid4()}{ext}"


def save_document_raw(file_bytes: bytes, object_key: str) -> None:
    """保存原始上传文件到 MinIO（默认模式调用；敏感模式由服务层跳过）。"""
    client = get_minio_client()
    ensure_bucket(client)
    # put_object 要求 file-like；用 BytesIO 包装原始字节
    client.put_object(
        get_settings().minio_bucket,
        object_key,
        io.BytesIO(file_bytes),
        length=len(file_bytes),
    )


def list_raw_objects(client: Minio | None = None) -> list[str]:
    """列举 bucket 内 raw-docs 前缀下的对象 key（用于验证/运维）。"""
    client = client or get_minio_client()
    bucket = get_settings().minio_bucket
    if not client.bucket_exists(bucket):
        return []
    return [obj.object_name for obj in client.list_objects(bucket, prefix=OBJECT_PREFIX)]
