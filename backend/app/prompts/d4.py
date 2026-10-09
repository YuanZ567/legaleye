"""D4 智能体提示词：第三方委托/共享（PIPL 第 21/22 条：委托协议 + 单独同意）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【第三方委托与共享】维度。审查委托处理是否约定双方权利义务，"
    "向第三方提供是否告知接收方信息并取得单独同意，委托协议是否完备。"
    "参考法条：个人信息保护法第 21/22 条。\n\n"
    "【合规要件清单】判违规前逐项核查：\n"
    "① 告知共享：是否告知共享对象、范围与目的？\n"
    "② 取得同意：向第三方提供是否取得您的单独同意（或属于法定例外，如事先获得明确授权、法律强制要求）？\n"
    "③ 同等保护：接收方是否有同等保护措施或签订数据保护协议？\n"
    "判定：①②③均满足 → 判 **compliant**（即使原文出现『共享/第三方/提供给』等词）；"
    "未取得单独同意且无例外才可判 nonCompliant。\n\n"
    "【示例·措辞模糊但明显违规】文档写道：『为开展营销活动，您的信息可能被提供给合作的推广方，"
    "以提升推广效果。』——向第三方提供个人信息未提及取得您的单独同意，"
    "即使『可能/以提升』模糊，也须判 nonCompliant（引用向第三方提供条款，如第二十二条）：\n"
    '{"dimension":"d4ThirdParty","verdict":"nonCompliant","level":"high",'
    '"clauseRef":"第二十二条","statuteVersion":"个人信息保护法(2021-11-01)",'
    '"description":"文档向第三方提供个人信息，未告知接收方信息亦未取得单独同意",'
    '"remediation":"取得单独同意并向您告知接收方信息",'
    '"confidence":0.87,"needsHumanReview":false,'
    '"evidence":{"text":"您的信息可能被提供给合作的推广方","charRange":[0,0]}}\n'
    "【示例·确属合规】文档写道：『向第三方共享您的信息前，我们会逐项取得您的单独同意，"
    "并告知您接收方名称与联系方式。』→ 判 compliant（已取得单独同意并告知，不因提及共享就判违规）。\n"
    "【示例·触发词但合规】文档写道：『我们不会与任何第三方共享您的个人信息，但以下情况除外："
    "（1）事先获得您明确的同意或授权…共享内容及目的详见清单。』"
    "→ 判 compliant（有同意前提 + 例外清单 + 共享告知，不因提及『共享』就判违规）。\n"
    "【示例·服务所必需+授权服务即合规】文档写道：『您可通过客户端使用我们、我们的关联方、"
    "我们合作的第三方服务方提供的各类服务，根据各服务实际提供方基于法定义务以及为向您提供服务所必需的要求，"
    "我们会向其提供或通过其获取您所使用服务的账号标识、订单、相关服务日志信息等必要信息。"
    "对于其他信息，您可以通过我们提供的信息授权服务进行信息共享。』"
    "→ 判 compliant（共享限于为向您提供服务所必需的字段 + 基于法定义务 + 其他信息走信息授权服务，"
    "有合规前提；不因出现『向其提供/第三方服务方/共享』就判违规）。"
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
    '"evidence":{"text":"原文摘录","charRange":[start,end]},'
    '"requirementCheck":[{"name":"要件名","status":"satisfied|missing|unknown","evidence":"原文摘录"}]}'
)

D4 = PromptSpec(
    dimension="d4",
    name="third_party_agent",
    system=_SYSTEM,
    user_template=_USER_TEMPLATE,
    output_schema=_OUTPUT_SCHEMA,
)
