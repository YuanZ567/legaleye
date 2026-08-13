"""D1 智能体提示词：个人信息收集合规（PIPL 最小必要/合法正当）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【个人信息收集】维度。审查文档中个人信息收集是否满足"
    "合法、正当、必要原则，收集范围是否限于实现处理目的的最小范围。"
    "参考法条：个人信息保护法第 5/6/13 条。"
)

_USER_TEMPLATE = (
    "请审查以下文档的个人信息收集合规性。\n\n"
    "【文档原文】\n{document}\n\n"
    "【检索到的相关法条】\n{retrieval}\n\n"
    "【审查上下文】\n{context}\n\n"
    "输出一条合规结论。"
)

_OUTPUT_SCHEMA = (
    '{"dimension":"d1Collection","verdict":"compliant|nonCompliant|pending|notApplicable",'
    '"level":"high|medium|low","clauseRef":"第X条第X款 或 待补",'
    '"statuteVersion":"法规名(年份)","description":"基于原文与法条的说明",'
    '"remediation":"整改建议","confidence":0.0-1.0,"needsHumanReview":bool,'
    '"evidence":{"text":"原文摘录","charRange":[start,end]}}'
)

D1 = PromptSpec(
    dimension="d1",
    name="collection_agent",
    system=_SYSTEM,
    user_template=_USER_TEMPLATE,
    output_schema=_OUTPUT_SCHEMA,
)
