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
    "注意：'dimension' 字段必须严格输出契约枚举值（如 d1Collection/d2Notice 等），"
    "不要输出中文维度名。\n"
    "【条款引用纪律】clauseRef 必须引用【检索到的相关法条】中实际出现的条款，"
    "且格式必须为阿拉伯数字的『第N条』（如『第6条』，禁止『第六条』『第六』等中文数字），"
    "仅当检索结果无命中时才输出『待补』。不得凭空捏造或引用检索结果之外的条款。\n"
    "【判定克制纪律】仅当文档原文存在明确、可引证的违规证据（给出 evidence.text 原文摘录）"
    "时才判 nonCompliant；若文档虽疑似有问题但证据不足或表述模糊，判 pending 并设 "
    "needsHumanReview=true；文档做法合规时判 compliant。严禁无证据臆断为违规。"
)
