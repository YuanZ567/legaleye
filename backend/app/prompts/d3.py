"""D3 智能体提示词：目的与最小化（PIPL 第 5/6 条：明确目的、直接相关、最小范围）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【目的与最小化】维度。审查处理目的是否明确合理、与目的直接相关，"
    "收集范围是否限于最小范围，保存期限是否为实现目的所必需的最短时间。"
    "参考法条：个人信息保护法第 5/6/19 条。"
)

_USER_TEMPLATE = (
    "请审查以下文档的处理目的与最小化合规性。\n\n"
    "【文档原文】\n{document}\n\n"
    "【检索到的相关法条】\n{retrieval}\n\n"
    "【审查上下文】\n{context}\n\n"
    "输出一条合规结论。"
)

_OUTPUT_SCHEMA = (
    '{"dimension":"d3Purpose","verdict":"compliant|nonCompliant|pending|notApplicable",'
    '"level":"high|medium|low","clauseRef":"第X条第X款 或 待补",'
    '"statuteVersion":"法规名(年份)","description":"说明",'
    '"remediation":"整改建议","confidence":0.0-1.0,"needsHumanReview":bool,'
    '"evidence":{"text":"原文摘录","charRange":[start,end]}}'
)

D3 = PromptSpec(
    dimension="d3",
    name="purpose_minimization_agent",
    system=_SYSTEM,
    user_template=_USER_TEMPLATE,
    output_schema=_OUTPUT_SCHEMA,
)
