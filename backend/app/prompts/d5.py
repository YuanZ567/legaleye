"""D5 智能体提示词：跨境提供（PIPL 第 38-40 条：安全评估/标准合同/单独同意）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【跨境提供】维度。审查向境外提供个人信息是否具备合法路径"
    "（安全评估/认证/标准合同/其他），是否取得单独同意并履行告知义务。"
    "\n\n【合规要件清单】判违规前逐项核查：\n"
    "① 单独同意：向境外提供是否取得您的单独同意？\n"
    "② 告知境外接收方：是否告知境外接收方名称、联系方式、处理目的、方式与个人信息种类？\n"
    "③ 合法出境路径：是否具备合法路径（数据出境安全评估/保护认证/标准合同/数据保护协议）？\n"
    "判定：①②③均满足 → 判 **compliant**（即使原文出现『跨境/境外/出境』等词）；"
    "未取得单独同意且无合法路径 → 才可判 nonCompliant。\n\n"
    "【硬性要求·clauseRef 引用纪律】"
    "\n- 必须先依据下方【检索到的相关法条】中的内容作答，禁止凭记忆写条款号；"
    "\n- clauseRef 必须取自【检索到的相关法条】里实际存在的条款号，禁止编造不存在的条款；"
    "\n- 若检索结果为空或未命中跨境相关条款，clauseRef 必须输出 '待补' 并设 needsHumanReview=true；"
    "\n- 条款号格式必须与检索结果一致（知识库为中文数字，如 '第三十九条'）。"
    "\n\n【示例】"
    "\n✅ 正确（引用检索结果中的条款，与知识库一致）："
    '\n  {"dimension":"d5CrossBorder","verdict":"nonCompliant","level":"high",'
    '"clauseRef":"第三十九条","statuteVersion":"个人信息保护法(2021-11-01)",'
    '"description":"文档未取得单独同意即向境外提供，违反个人信息保护法第39条",'
    '"remediation":"补取单独同意并履行告知义务","confidence":0.9,"needsHumanReview":false}'
    "\n❌ 错误（检索中不存在的条款）："
    '\n  {"clauseRef":"第二条"}  ← 若检索结果中没有第二条，禁止这样输出'
    "\n\n【示例·措辞模糊但明显违规】文档写道：『您的信息将存储在境外的服务器，"
    "您注册使用本服务即视为同意该跨境传输。』——未取得单独同意、未告知出境处理方式，"
    "即使『即视为同意』模糊，也须判 nonCompliant（引用跨境条款，如第三十九条）：\n"
    '{"dimension":"d5CrossBorder","verdict":"nonCompliant","level":"high",'
    '"clauseRef":"第三十九条","statuteVersion":"个人信息保护法(2021-11-01)",'
    '"description":"文档将信息存储于境外服务器，注册即视为同意跨境传输，未取得单独同意",'
    '"remediation":"取得单独同意并履行告知义务",'
    '"confidence":0.89,"needsHumanReview":false,'
    '"evidence":{"text":"您的信息将存储在境外的服务器","charRange":[0,0]}}\n'
    "【示例·确属合规】文档写道：『向境外提供您的个人信息前，我们将依法完成数据出境安全评估，"
    "并取得您的单独同意。』→ 判 compliant（已满足评估与单独同意，不因提及境外就判违规）。\n"
    "【示例·触发词但合规】文档写道：『如您使用跨境交易服务，我们会单独获取您的授权同意，"
    "并要求接收方按照双方签署的数据保护协议处理您的个人信息。』"
    "→ 判 compliant（单独同意 + DPA 齐备，不因提及『跨境/境外』就判违规）。\n"
    "【条款选择·区分】若文档核心违规是『未取得单独同意即跨境传输』→ 引用『第三十九条』；"
    "若核心违规是『向境外提供重要数据/关键信息基础设施运营者未申报数据出境安全评估』→ "
    "引用『第四十条』。注意区分，勿混用。"
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
    '"evidence":{"text":"原文摘录","charRange":[start,end]},'
    '"requirementCheck":[{"name":"要件名","status":"satisfied|missing|unknown","evidence":"原文摘录"}]}'
)

D5 = PromptSpec(
    dimension="d5",
    name="cross_border_agent",
    system=_SYSTEM,
    user_template=_USER_TEMPLATE,
    output_schema=_OUTPUT_SCHEMA,
)
