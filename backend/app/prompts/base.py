"""Prompt 数据结构与注册表基础（M4-2）。

- 所有提示词集中在 prompts/ 目录，禁止在业务代码中散落 prompt 字符串；
- 每维度一个 .py，输出 schema 强制（JSON 字段枚举约束）；
- 通用纪律写入 system："依据检索结果而非记忆"，检索无命中输出 '待补'。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptSpec:
    """一个智能体的提示词（system + user 模板 + 输出 schema 说明）。"""

    dimension: str  # 维度标识（D1-D6）
    name: str  # 智能体名
    system: str  # system prompt（含纪律）
    user_template: str  # user prompt 模板（{context}/{retrieval}/{document} 占位）
    output_schema: str  # 输出 JSON schema 说明（强制枚举/字段）

    def render_user(self, **kwargs: str) -> str:
        """填充 user_template 占位符。"""
        return self.user_template.format(**kwargs)


# 通用纪律（拼入各智能体 system）
COMMON_SYSTEM = (
    "你是一名数据合规审查专家。必须严格依据下方提供的检索结果与文档原文作答，"
    "不得依据个人记忆或推测。若检索结果无命中相关法条，请在 clauseRef 输出 '待补'，"
    "并设置 needsHumanReview=true。只输出符合 schema 的 JSON，不要多余解释。"
)
