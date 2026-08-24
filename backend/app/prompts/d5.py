"""D5 智能体提示词：跨境提供（PIPL 第 38-40 条：安全评估/标准合同/单独同意）。"""

from app.prompts.base import COMMON_SYSTEM, PromptSpec

_SYSTEM = COMMON_SYSTEM + (
    "\n你负责【跨境提供】维度。审查向境外提供个人信息是否具备合法路径"
    "（安全评估/认证/标准合同/其他），是否取得单独同意并履行告知义务。"
    "\n\n【硬性要求·clauseRef 引用纪律】"
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
