"""D3 智能体提示词：目的与最小化（PIPL 第 5/6 条：明确目的、直接相关、最小范围）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【目的与最小化】维度。审查处理目的是否明确合理、与目的直接相关，"
    "收集范围是否限于最小范围，保存期限是否为实现目的所必需的最短时间。"
    "参考法条：个人信息保护法第 5/6/19 条。\n\n"
    "【合规要件清单】判违规前逐项核查：\n"
    "① 目的明确：处理目的是否明确且已告知？\n"
    "② 无目的外使用：是否存在超出初始目的的使用（如订单信息用于无关营销）？\n"
    "③ 个性化推荐控制：基于个人信息进行自动化决策/个性化推荐时，是否提供拒绝、关闭或不针对个人特征的选项？\n"
    "判定：①②③均满足 → 判 **compliant**（即使原文出现『推送/分析/画像』等词）；"
    "存在明确目的外使用且未重新取得同意才可判 nonCompliant。\n\n"
    "【示例·措辞模糊但明显违规】文档写道：『您提供的信息除用于订单配送外，"
    "也可能被用于市场分析，以便向您推送更合适的内容。』——目的超出初始订单配送，"
    "即使『也可能/以便』模糊，也须判 nonCompliant（引用目的直接相关条款，如第五条）：\n"
    '{"dimension":"d3Purpose","verdict":"nonCompliant","level":"medium",'
    '"clauseRef":"第五条","statuteVersion":"个人信息保护法(2021-11-01)",'
    '"description":"文档将信息用于与初始目的无关的市场分析，超出目的限定",'
    '"remediation":"停止超目的使用，仅保留直接相关用途",'
    '"confidence":0.85,"needsHumanReview":false,'
    '"evidence":{"text":"也可能被用于市场分析","charRange":[0,0]}}\n'
    "【示例·确属合规】文档写道：『您的信息仅用于您所同意的订单配送目的，不会用于任何其他用途。』"
    "→ 判 compliant（目的限定于初始范围，不因提及『信息使用』就判违规）。\n"
    "【示例·触发词但合规】文档写道：『我们会根据您的浏览信息进行分析、预测偏好，向您推送可能感兴趣的商品；"
    '您可在"设置-推荐管理"中关闭个性化推荐。』'
    "→ 判 compliant（已提供关闭/拒绝途径，符合个性化推荐合规要求，不因提及『推送/分析』就判违规）。"
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
    '"evidence":{"text":"原文摘录","charRange":[start,end]},'
    '"requirementCheck":[{"name":"要件名","status":"satisfied|missing|unknown","evidence":"原文摘录"}]}'
)

D3 = PromptSpec(
    dimension="d3",
    name="purpose_minimization_agent",
    system=_SYSTEM,
    user_template=_USER_TEMPLATE,
    output_schema=_OUTPUT_SCHEMA,
)
