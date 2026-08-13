"""D2 智能体提示词：告知与同意（PIPL 第 17/14 条：显著告知 + 单独同意）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【告知与同意】维度。审查文档是否以显著方式清晰告知处理目的/方式/范围，"
    "敏感信息是否取得单独同意，撤回同意的便利性。参考法条：个人信息保护法第 14/17 条。"
)

_USER_TEMPLATE = (
    "请审查以下文档的告知与同意合规性。\n\n"
    "【文档原文】\n{document}\n\n"
    "【检索到的相关法条】\n{retrieval}\n\n"
    "【审查上下文】\n{context}\n\n"
    "输出一条合规结论。"
)

_OUTPUT_SCHEMA = (
    '{"dimension":"d2Notice","verdict":"compliant|nonCompliant|pending|notApplicable",'
    '"level":"high|medium|low","clauseRef":"第X条第X款 或 待补",'
    '"statuteVersion":"法规名(年份)","description":"说明",'
    '"remediation":"整改建议","confidence":0.0-1.0,"needsHumanReview":bool,'
    '"evidence":{"text":"原文摘录","charRange":[start,end]}}'
)

D2 = PromptSpec(
    dimension="d2",
    name="notice_consent_agent",
    system=_SYSTEM,
    user_template=_USER_TEMPLATE,
    output_schema=_OUTPUT_SCHEMA,
)
