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
    "【判定纪律·抓违规】审查目的是发现违规。只要能从文档原文引证其行为与相关法条不符"
    "（给出 evidence.text 原文摘录），就判 nonCompliant；**即使原文措辞隐晦、含糊、"
    "用『可能/或许/以便/视为同意』等软化词，只要行为实质违规仍须判 nonCompliant**。\n"
    "【判定纪律·防误报(关键)】**不要对每个维度都判违规**。仅在文档原文明确涉及该维度的"
    "处理行为**且该行为确实违规**时才判 nonCompliant。以下情况不得判违规：\n"
    "- 文档为该维度**提供了合规措施**（如已取得同意、已提供删除/更正渠道、已做最小化、"
    "已取得单独同意）→ 判 **compliant**，即使该维度在文中出现；\n"
    "- 文档**完全未涉及**该维度的处理行为 → 判 **notApplicable**（不要从无关句臆断违规）；\n"
    "必须给出能支撑 nonCompliant 的具体违规原文证据；若拿不出违规证据，宁可判 "
    "compliant/notApplicable 也不要臆断。严禁把合规措施误判为违规。\n"
    "【报告数量克制】一份文档通常只有少数几个维度（0-3 个）真正违规。不要为了覆盖所有维度"
    "而逐一判违规；多数维度应判 compliant 或 notApplicable。只有当某维度存在**明确且独立**的"
    "违规证据时才报告该维度违规。若你对某维度拿不准，优先判 notApplicable 而非臆断违规。"
)
