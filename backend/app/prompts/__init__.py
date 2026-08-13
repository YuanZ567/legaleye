"""提示词注册表（M4-2）：集中管理 D1-D6 各智能体提示词。

用法：`get_prompt("d1")` / `get_prompt("d5")` 返回 PromptSpec。
禁止在业务代码中散落 prompt 字符串（ARCHITECTURE 3 纪律）。
"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec
from app.prompts.d1 import D1
from app.prompts.d2 import D2
from app.prompts.d3 import D3
from app.prompts.d4 import D4
from app.prompts.d5 import D5
from app.prompts.d6 import D6

# 维度 → PromptSpec 注册表
PROMPTS: dict[str, PromptSpec] = {
    "d1": D1,
    "d2": D2,
    "d3": D3,
    "d4": D4,
    "d5": D5,
    "d6": D6,
}


def get_prompt(dimension: str) -> PromptSpec:
    """按维度标识获取 PromptSpec；未知维度抛 KeyError。"""
    return PROMPTS[dimension]


__all__ = ["COMMON_SYSTEM", "PROMPTS", "PromptSpec", "get_prompt"]
