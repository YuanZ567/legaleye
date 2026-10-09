"""模型配置服务（M8-3）：四 provider 保存/激活/测试。

- Key Fernet 密文存储（绝不出 API，仅 apiKeyTail 尾号 4 位脱敏）；
- is_active 单 provider：切换激活事务保证（停旧启用）；
- test_model 真实验证：用临时 Key 打通 provider，成功才允许保存；
- 无效 Key 在保存前拦截（避免后续审查失败）。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Provider
from app.core.exceptions import ValidationError
from app.core.security import decrypt_secret, encrypt_secret
from app.llm.factory import PROVIDER_BASE_URLS
from app.models import ModelConfig

# provider → 显示名（契约 displayName）
PROVIDER_DISPLAY: dict[Provider, str] = {
    Provider.BAILIAN: "阿里云百炼",
    Provider.DEEPSEEK: "DeepSeek",
    Provider.OPENAI: "OpenAI（GPT）",
    Provider.ANTHROPIC: "Anthropic",
    Provider.MODELSCOPE: "魔搭社区",
    Provider.ZHIPU: "智谱 BigModel",
    Provider.SILICONFLOW: "硅基流动",
}


def _api_key_tail(cipher: str) -> str:
    """Key 尾号 4 位脱敏（从密文解密取末 4 位；解密失败返回 ''）。"""
    try:
        plain = decrypt_secret(cipher)
        return plain[-4:] if plain else ""
    except Exception:
        return ""


def to_dict(cfg: ModelConfig) -> dict:
    """序列化为契约 ModelConfig（apiKeyTail 脱敏，绝不含明文 Key）。"""
    return {
        "id": str(cfg.id),
        "provider": cfg.provider.value,
        "displayName": PROVIDER_DISPLAY.get(cfg.provider, cfg.provider.value),
        "model": cfg.model,
        "apiKeyTail": _api_key_tail(cfg.api_key_encrypted),
        "isActive": cfg.is_active,
    }


def create_model(*, db: Session, provider: Provider, api_key: str, model: str) -> ModelConfig:
    """保存模型配置（Key Fernet 加密；首个模型自动激活）。"""
    if not api_key.strip():
        raise ValidationError("API Key 不能为空", code="api_key_required")

    # 同 provider 同 model 去重（避免重复配置）
    exists = db.scalar(
        select(ModelConfig).where(ModelConfig.provider == provider, ModelConfig.model == model)
    )
    if exists is not None:
        raise ValidationError("该 provider 已配置相同模型", code="model_exists")

    has_active = db.scalar(select(ModelConfig.id).where(ModelConfig.is_active.is_(True)).limit(1))
    cfg = ModelConfig(
        provider=provider,
        api_key_encrypted=encrypt_secret(api_key),
        model=model,
        is_active=has_active is None,  # 无 active 则首个激活
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def activate_model(*, db: Session, model_id: uuid.UUID) -> ModelConfig | None:
    """切换激活（事务：停用其他 active → 启用目标）。"""
    cfg = db.get(ModelConfig, model_id)
    if cfg is None:
        return None
    # 停用所有其他 active（单 provider 保证）
    db.execute(
        ModelConfig.__table__.update()
        .where(ModelConfig.is_active.is_(True))
        .values(is_active=False)
    )
    cfg.is_active = True
    db.commit()
    db.refresh(cfg)
    return cfg


def list_models(db: Session) -> list[dict]:
    """列出所有模型配置（含 apiKeyTail 脱敏）。"""
    configs = db.scalars(select(ModelConfig).order_by(ModelConfig.created_at)).all()
    return [to_dict(c) for c in configs]


def delete_model(*, db: Session, model_id: uuid.UUID) -> bool:
    """删除模型配置（激活中的模型不允许删除，避免审查无可用模型）。

    返回是否删除；不存在返回 False。
    """
    cfg = db.get(ModelConfig, model_id)
    if cfg is None:
        return False
    if cfg.is_active:
        raise ValidationError("激活中的模型不可删除，请先启用其他模型", code="model_active")
    db.delete(cfg)
    db.commit()
    return True


def test_model(*, provider: Provider, api_key: str, model: str) -> dict:
    """真实验证：用临时 Key 打通 provider（chat completion 最小请求）。

    返回 {"ok": True} 或抛 ValidationError（无效 Key 保存前拦截）。
    """
    if not api_key.strip():
        raise ValidationError("API Key 不能为空", code="api_key_required")

    try:
        if provider == Provider.ANTHROPIC:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key, timeout=30)
            resp = client.messages.create(
                model=model, max_tokens=16, messages=[{"role": "user", "content": "ping"}]
            )
            _ = resp  # 成功即连通
        else:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=PROVIDER_BASE_URLS[provider], timeout=30)
            resp = client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": "ping"}], max_tokens=16
            )
            _ = resp
        return {"ok": True}
    except Exception as exc:
        raise ValidationError(f"模型连接失败：{exc}", code="model_test_failed") from exc
