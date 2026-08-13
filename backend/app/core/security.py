"""安全工具：Fernet 对称加解密（ARCHITECTURE L2 纪律）。

- API Key 以 Fernet 密文存储（ModelConfig.api_key_encrypted），仅后端可解密；
- 解密后的 Key 只在内存使用，绝不落日志/出 API（前端永不接触 Key 明文）。

密钥来源：config.legaleye_secret_key（环境变量 LEGALEYE_SECRET_KEY）。
"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class SecurityError(Exception):
    """加解密失败。"""


def _fernet() -> Fernet:
    key = get_settings().legaleye_secret_key
    if not key:
        raise SecurityError("未配置 LEGALEYE_SECRET_KEY，无法加解密")
    return Fernet(key.encode("utf-8"))


def encrypt_secret(plaintext: str) -> str:
    """加密明文（API Key 等 L2 凭据），返回密文串。"""
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """解密密文为明文；解密失败抛 SecurityError（不静默返回）。"""
    if not ciphertext:
        return ""
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise SecurityError("密文无效或密钥不匹配，无法解密") from None
