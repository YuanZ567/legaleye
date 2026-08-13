"""初始化 ModelConfig：把百炼 API Key 以 Fernet 密文写入数据库。

用法（backend 虚拟环境，从仓库根执行）：
    cd backend && .venv/Scripts/python.exe ../scripts/init_model_config.py

读取 os.environ["OPENAI_API_KEY"]（百炼 DashScope 兼容模式的 Key），
经 core.security.encrypt_secret（Fernet）加密后写入 ModelConfig：
    provider = BAILIAN
    model    = qwen3.7-flash-2026-07-15
    is_active = True

【选型说明：为什么用 qwen3.7-flash-2026-07-15】
- 属于百炼免费额度内的最新 flash 模型，审查场景（六维抽取 + Critic 复核）性价比高；
- 在官方免费额度内，避免产生费用；flash 系列推理速度满足"≤100 页 PDF 报告 ≤3 分钟"验收；
- 明确不用 qwen-turbo：qwen-turbo 不在免费额度内，会产生费用。

幂等：若已存在该 provider 的活跃配置，则更新模型名与密文；否则新增。
"""

import os
import sys
from pathlib import Path

# 允许直接从 scripts/ 运行（不依赖安装）
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.core.enums import Provider  # noqa: E402
from app.core.security import encrypt_secret  # noqa: E402
from app.models.model_config import ModelConfig  # noqa: E402

# 目标模型（百炼免费额度内最新 flash；不要用 qwen-turbo，不在免费额度）
TARGET_MODEL = "qwen3.7-flash-2026-07-15"


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("[init_model_config] 未设置 OPENAI_API_KEY 环境变量")
        sys.exit(1)

    cipher = encrypt_secret(api_key)

    with SessionLocal() as db:
        existing = db.scalar(
            select(ModelConfig).where(ModelConfig.provider == Provider.BAILIAN)
        )
        if existing is not None:
            existing.api_key_encrypted = cipher
            existing.model = TARGET_MODEL
            existing.is_active = True
            db.commit()
            print(f"[init_model_config] 更新 BAILIAN 配置 -> {TARGET_MODEL}")
        else:
            db.add(
                ModelConfig(
                    provider=Provider.BAILIAN,
                    api_key_encrypted=cipher,
                    model=TARGET_MODEL,
                    is_active=True,
                )
            )
            db.commit()
            print(f"[init_model_config] 新增 BAILIAN 配置 -> {TARGET_MODEL}")

        print("[init_model_config] Key 已 Fernet 加密存储（L2，永不出 API）")


if __name__ == "__main__":
    main()
