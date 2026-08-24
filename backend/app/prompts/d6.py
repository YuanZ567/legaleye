"""D6 智能体提示词：数据主体权利（PIPL 第 45-48 条：查询/复制/更正/删除/撤回同意）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【数据主体权利】维度。审查文档是否为个人提供查询、复制、更正、删除"
    "其个人信息的便捷途径，是否支持撤回同意。参考法条：个人信息保护法第 45-48 条。\n\n"
    "【示例·措辞模糊但明显违规】文档写道：『您的个人信息将被长期保存，以备后续服务所需。』"
    "——未提供删除、更正、复制的渠道，即使『以备后续所需』模糊，也须判 nonCompliant"
    "（引用数据主体权利条款，如第八条）：\n"
    '{"dimension":"d6DataRights","verdict":"nonCompliant","level":"medium",'
    '"clauseRef":"第八条","statuteVersion":"个人信息保护法(2021-11-01)",'
    '"description":"文档未提供查询、更正、删除个人信息的便捷途径",'
    '"remediation":"在个人中心提供删除、更正、复制功能",'
    '"confidence":0.86,"needsHumanReview":false,'
    '"evidence":{"text":"您的个人信息将被长期保存","charRange":[0,0]}}\n'
    "【示例·确属合规】文档写道：『您可通过个人中心随时查询、更正、删除您的个人信息，"
    "并可撤回同意。』→ 判 compliant（已提供便捷途径，不因提及『长期保存』就判违规）。"
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
