"""D2 智能体提示词：告知与同意（PIPL 第 17/14 条：显著告知 + 单独同意）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【告知与同意】维度。审查文档是否以显著方式清晰告知处理目的/方式/范围，"
    "敏感信息是否取得单独同意，撤回同意的便利性。参考法条：个人信息保护法第 14/17 条。\n\n"
    "【合规要件清单】判违规前逐项核查：\n"
    "① 显著告知：是否以显著方式告知处理目的、方式、个人信息种类与保存期限？\n"
    "② 敏感信息单独同意：敏感信息处理是否取得单独同意？\n"
    "③ 撤回同意：是否提供撤回同意途径？\n"
    "判定：①②③均满足 → 判 **compliant**（即使原文出现『处理/收集/共享』等词）；"
    "存在缺失要件才可判 nonCompliant。\n\n"
    "【示例·措辞模糊但明显违规】文档写道：『我们可能对您的个人信息进行必要的处理，"
    "以便提升您的使用体验。』——未告知处理的具体种类、目的、方式与保存期限，"
    "即使措辞模糊，也须判 nonCompliant（引用告知条款，如第十七条）：\n"
    '{"dimension":"d2Notice","verdict":"nonCompliant","level":"high",'
    '"clauseRef":"第十七条","statuteVersion":"个人信息保护法(2021-11-01)",'
    '"description":"文档未以显著方式清晰告知处理种类、目的与保存期限",'
    '"remediation":"补全告知事项并显著展示",'
    '"confidence":0.88,"needsHumanReview":false,'
    '"evidence":{"text":"我们可能对您的个人信息进行必要的处理","charRange":[0,0]}}\n'
    "【示例·确属合规】文档写道：『我们已以显著方式向您告知处理个人信息的种类、目的、方式与保存期限，"
    "并取得您的同意。』→ 判 compliant（已充分告知，不因提及处理就判违规）。\n"
    "【示例·触发词但合规】文档以章节形式完整告知：『本指引将帮助您了解以下内容："
    "一、我们如何收集和使用您的信息；二、我们如何共享您的信息…您可随时撤回同意。』"
    "→ 判 compliant（完整告知 + 撤回途径，不因提及『收集/共享』就判违规）。"
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
    '"evidence":{"text":"原文摘录","charRange":[start,end]},'
    '"requirementCheck":[{"name":"要件名","status":"satisfied|missing|unknown","evidence":"原文摘录"}]}'
)

D2 = PromptSpec(
    dimension="d2",
    name="notice_consent_agent",
    system=_SYSTEM,
    user_template=_USER_TEMPLATE,
    output_schema=_OUTPUT_SCHEMA,
)
