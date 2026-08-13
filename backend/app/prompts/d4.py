"""D4 智能体提示词：第三方委托/共享（PIPL 第 21/22 条：委托协议 + 单独同意）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【第三方委托与共享】维度。审查委托处理是否约定双方权利义务，"
    "向第三方提供是否告知接收方信息并取得单独同意，委托协议是否完备。"
    "参考法条：个人信息保护法第 21/22 条。"
)

_USER_TEMPLATE = (
    "请审查以下文档的第三方委托与共享合规性。\n\n"
    "【文档原文】\n{document}\n\n"
    "【检索到的相关法条】\n{retrieval}\n\n"
    "【审查上下文】\n{context}\n\n"
    "输出一条合规结论。"
)

_OUTPUT_SCHEMA = (
    '{"dimension":"d4ThirdParty","verdict":"compliant|nonCompliant|pending|notApplicable",'
    '"level":"high|medium|low","clauseRef":"第X条第X款 或 待补",'
    '"statuteVersion":"法规名(年份)","description":"说明",'
    '"remediation":"整改建议","confidence":0.0-1.0,"needsHumanReview":bool,'
    '"evidence":{"text":"原文摘录","charRange":[start,end]}}'
)

D4 = PromptSpec(
    dimension="d4",
    name="third_party_agent",
    system=_SYSTEM,
    user_template=_USER_TEMPLATE,
    output_schema=_OUTPUT_SCHEMA,
)
