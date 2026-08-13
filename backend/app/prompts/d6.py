"""D6 智能体提示词：数据主体权利（PIPL 第 45-48 条：查询/复制/更正/删除/撤回同意）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【数据主体权利】维度。审查文档是否为个人提供查询、复制、更正、删除"
    "其个人信息的便捷途径，是否支持撤回同意。参考法条：个人信息保护法第 45-48 条。"
)

_USER_TEMPLATE = (
    "请审查以下文档的数据主体权利合规性。\n\n"
    "【文档原文】\n{document}\n\n"
    "【检索到的相关法条】\n{retrieval}\n\n"
    "【审查上下文】\n{context}\n\n"
    "输出一条合规结论。"
)

_OUTPUT_SCHEMA = (
    '{"dimension":"d6DataRights","verdict":"compliant|nonCompliant|pending|notApplicable",'
    '"level":"high|medium|low","clauseRef":"第X条第X款 或 待补",'
    '"statuteVersion":"法规名(年份)","description":"说明",'
    '"remediation":"整改建议","confidence":0.0-1.0,"needsHumanReview":bool,'
    '"evidence":{"text":"原文摘录","charRange":[start,end]}}'
)

D6 = PromptSpec(
    dimension="d6",
    name="data_rights_agent",
    system=_SYSTEM,
    user_template=_USER_TEMPLATE,
    output_schema=_OUTPUT_SCHEMA,
)
