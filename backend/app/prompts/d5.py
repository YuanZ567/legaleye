"""D5 智能体提示词：跨境提供（PIPL 第 38-40 条：安全评估/标准合同/单独同意）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【跨境提供】维度。审查向境外提供个人信息是否具备合法路径"
    "（安全评估/认证/标准合同/其他），是否取得单独同意并履行告知义务。"
    "参考法条：个人信息保护法第 39/40 条、数据出境安全评估办法第 3 条。"
)

_USER_TEMPLATE = (
    "请审查以下文档的跨境提供合规性。\n\n"
    "【文档原文】\n{document}\n\n"
    "【检索到的相关法条】\n{retrieval}\n\n"
    "【图谱出境风险提示】\n{graph_risk}\n\n"
    "【审查上下文】\n{context}\n\n"
    "输出一条合规结论。"
)

_OUTPUT_SCHEMA = (
    '{"dimension":"d5CrossBorder","verdict":"compliant|nonCompliant|pending|notApplicable",'
    '"level":"high|medium|low","clauseRef":"第X条第X款 或 待补",'
    '"statuteVersion":"法规名(年份)","description":"说明",'
    '"remediation":"整改建议","confidence":0.0-1.0,"needsHumanReview":bool,'
    '"evidence":{"text":"原文摘录","charRange":[start,end]}}'
)

D5 = PromptSpec(
    dimension="d5",
    name="cross_border_agent",
    system=_SYSTEM,
    user_template=_USER_TEMPLATE,
    output_schema=_OUTPUT_SCHEMA,
)
