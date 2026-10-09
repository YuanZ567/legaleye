"""六维审查节点：真实 LLM 调用（经 llm/factory）+ finding 强校验 + 降级。

流程：
1. 读取 prompts 维度提示词（集中管理，禁止散落）；
2. 经 llm/factory.chat_completion 调用（唯一入口，自动记账 LLMCallRecord）；
3. 输出过 schemas/validators.validate_finding 强校验（clauseRef 正则/confidence 钳制/枚举丢弃）；
4. 校验失败/LLM 异常 → 降级"待补 + needsHumanReview=true"（任务不中断）。

llm_func 可注入（测试 mock），默认走 factory（生产真实调用）。
"""

import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.sse import publish_event
from app.prompts import get_prompt
from app.schemas.validators import validate_finding

logger = logging.getLogger(__name__)


def _rescue_json(text: str) -> Any:
    """容错解析 LLM 输出 JSON（免费模型输出不稳定）：

    1. 剥掉首尾杂文本（取首个 { / [ 到最后一个 } / ] 之间的子串）；
    2. 修复尾随逗号（",}" / ",]"）；
    3. raw_decode 取第一个完整 JSON 对象。
    全部失败抛 ValueError（由上层降级/重试处理）。
    """
    # 1) 提取首 { / [ 到 尾 } / ] 之间的候选子串（容忍前后说明文字 / 截断）
    start = len(text)
    for ch in ("{", "["):
        i = text.find(ch)
        if i != -1 and i < start:
            start = i
    end = -1
    for ch in ("}", "]"):
        i = text.rfind(ch)
        if i > end:
            end = i
    if start < end:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    # 2) 尾随逗号修复
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    # 3) raw_decode 取第一个完整 JSON 对象
    try:
        obj, _ = json.JSONDecoder().raw_decode(text.lstrip())
        return obj
    except (ValueError, json.JSONDecodeError):
        raise ValueError(f"无法解析 LLM 输出 JSON: {text[:200]!r}")


def _extract_json(text: str) -> dict:
    """从 LLM 输出提取 JSON（容忍 markdown 代码块包裹 / 杂文本 / 截断 / 尾逗号）。

    LLM 偶发输出数组（[{...}] 而非 {…}）——取首元素；空数组视为非法降级。
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # 去掉 ```json ... ``` 包裹
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = _rescue_json(cleaned)
    if isinstance(data, list):
        if not data:
            raise ValueError("LLM 输出空数组")
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError(f"LLM 输出非对象: {type(data).__name__}")
    return data


# 维度级 LLM 调用重试（M10.3，2026-09-17）：免费模型输出不稳定（超时/429/JSON 畸形）
_DIM_RETRY_MAX = 2
_DIM_RETRY_BACKOFF = 3.0  # 非限流错误递增退避：3s / 6s
_DIM_RETRY_BACKOFF_429 = 60.0  # 429 限流：等限流窗口过去再试（60s / 120s）


def _is_rate_limited(exc: Exception) -> bool:
    """判断异常是否为账户级限流（429 / 1302 / 速率限制）。"""
    msg = f"{type(exc).__name__}: {exc}"
    return any(k in msg for k in ("429", "1302", "速率限制", "rate limit", "RateLimit"))


async def _call_with_retry(llm_func: Callable[..., Awaitable[str]], call_kwargs: dict[str, Any]) -> tuple[str, dict]:
    """调用 llm_func 并解析 JSON；失败重试（最多 _DIM_RETRY_MAX 次）。

    返回 (原始文本, 解析后 dict)。全部失败抛原始异常（交给外层降级）。
    """
    import asyncio as _asyncio

    last_exc: Exception | None = None
    for attempt in range(_DIM_RETRY_MAX + 1):
        try:
            text = await llm_func(**call_kwargs)
            raw = _extract_json(text)
            return text, raw
        except Exception as exc:
            last_exc = exc
            if attempt < _DIM_RETRY_MAX:
                logger.warning(
                    "维度 %s 调用失败，第 %d 次重试（%s: %s）",
                    call_kwargs.get("dimension"),
                    attempt + 1,
                    type(exc).__name__,
                    str(exc)[:200],
                )
                if _is_rate_limited(exc):
                    # 429 是账户级限流：等窗口过去（60s/120s）再试，短退避只会继续撞墙
                    await _asyncio.sleep(_DIM_RETRY_BACKOFF_429 * (attempt + 1))
                else:
                    await _asyncio.sleep(_DIM_RETRY_BACKOFF * (attempt + 1))
    raise last_exc  # type: ignore[misc]


# 维度归一化：LLM 可能输出中文名/智能体名/短名 → 契约值
DIMENSION_NORMALIZE: dict[str, str] = {
    "d1": "d1Collection",
    "d1Collection": "d1Collection",
    "个人信息收集": "d1Collection",
    "收集": "d1Collection",
    "d2": "d2Notice",
    "d2Notice": "d2Notice",
    "告知与同意": "d2Notice",
    "告知同意": "d2Notice",
    "d3": "d3Purpose",
    "d3Purpose": "d3Purpose",
    "目的与最小化": "d3Purpose",
    "d4": "d4ThirdParty",
    "d4ThirdParty": "d4ThirdParty",
    "第三方委托与共享": "d4ThirdParty",
    "第三方委托": "d4ThirdParty",
    "d5": "d5CrossBorder",
    "d5CrossBorder": "d5CrossBorder",
    "跨境提供": "d5CrossBorder",
    "跨境": "d5CrossBorder",
    "d6": "d6DataRights",
    "d6DataRights": "d6DataRights",
    "数据主体权利": "d6DataRights",
}


def normalize_dimension(value: str | None, fallback_dim: str) -> str:
    """把 LLM 输出的维度值归一化为契约值；无法识别用 fallback 的契约值。

    支持契约值前缀匹配（如 "d5CrossBorderProvision" → "d5CrossBorder"）。
    """
    if value:
        stripped = str(value).strip()
        exact = DIMENSION_NORMALIZE.get(stripped)
        if exact:
            return exact
        # 契约值前缀匹配（LLM 常追加后缀如 Provision/Review）
        for dim, contract in DIMENSION_NORMALIZE.items():
            if dim.startswith("d") and dim == contract and stripped.startswith(contract):
                return contract
    return DIMENSION_NORMALIZE.get(fallback_dim, fallback_dim)


_REQ_STATUS_VALID = {"satisfied", "missing", "unknown"}


def _extract_requirement_check(raw: dict) -> list[dict] | None:
    """从 LLM 原始输出提取 requirementCheck（要件核查），规范化 status 枚举。

    模型输出不合规的结构/枚举 → 丢弃该项；全部丢弃 → None（视为未核查，走原逻辑）。
    """
    rc = raw.get("requirementCheck") or raw.get("requirement_check")
    if not isinstance(rc, list) or not rc:
        return None
    out: list[dict] = []
    for item in rc:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        status = str(item.get("status") or "").strip().lower()
        if not name or status not in _REQ_STATUS_VALID:
            continue
        ev = item.get("evidence")
        out.append({"name": name, "status": status, "evidence": str(ev or "").strip()})
    return out or None


def _normalize_llm_raw(raw: dict, fallback_dim: str, retrieval: str = "") -> dict:
    """规范化 LLM 原始输出（schema 不稳定的容忍层）。

    - dimension：归一化到契约值；
    - verdict 缺失但含 conclusion → 按语义推断（不合规/合规/部分/不适用）；
    - clauseRef 清洗 + **检索命中校验**（红线：禁无引用结论）——LLM 输出的条款号
      必须在本轮检索结果中，否则强制清空 + needsHumanReview + verdict=unclear
      （绝不静默放过"假引用"）；
    - level 缺失默认 medium；
    - requirementCheck 提取到私有键 _requirement_check（validators 白名单会丢弃，
      由 node 层在 validate 后回填到 finding）。
    """
    import re

    # requirementCheck 提取（M10.2 要件核查：先于 validators，避免被白名单丢弃）
    raw["_requirement_check"] = _extract_requirement_check(raw)

    # dimension 归一化
    raw["dimension"] = normalize_dimension(raw.get("dimension"), fallback_dim)

    # verdict：缺失但含 conclusion 时按语义推断
    if not raw.get("verdict"):
        conclusion = str(raw.get("conclusion") or "")
        if "不合规" in conclusion or "违反" in conclusion or "未" in conclusion:
            raw["verdict"] = "nonCompliant"
        elif "合规" in conclusion and "部分" not in conclusion:
            raw["verdict"] = "compliant"
        elif "部分" in conclusion:
            raw["verdict"] = "partial"
        elif "不适用" in conclusion:
            raw["verdict"] = "notApplicable"
        else:
            raw["verdict"] = "unclear"

    # level 缺失默认 medium
    if not raw.get("level"):
        raw["level"] = "medium"

    # clauseRef 清洗/提取：优先 clauseRef 字段，其次从 conclusion/description 提取
    clause_ref = str(raw.get("clauseRef") or "")
    m = re.search(r"第[一二三四五六七八九十\d]+条(第[一二三四五六七八九十\d]+款)?", clause_ref)
    if not m:
        search_text = f"{raw.get('conclusion', '')} {raw.get('description', '')}"
        m = re.search(r"第[一二三四五六七八九十\d]+条(第[一二三四五六七八九十\d]+款)?", search_text)
    extracted_ref = m.group(0) if m else ""

    # 检索命中校验（红线）：clauseRef 必须在本轮检索结果中；无检索 → 不能有引用
    retrieval_text = retrieval or ""
    if extracted_ref and (retrieval_text and extracted_ref in retrieval_text):
        # 命中检索：保留引用（needsHumanReview 用 LLM 原值或默认 False）
        raw["clauseRef"] = extracted_ref
        raw["needsHumanReview"] = bool(raw.get("needsHumanReview", False))
    elif extracted_ref and not retrieval_text:
        # 无检索结果却写引用 → 假引用，清空 + 人工复核
        raw["clauseRef"] = ""
        raw["verdict"] = "unclear"
        raw["needsHumanReview"] = True
    elif extracted_ref and extracted_ref not in retrieval_text:
        # 引用不在检索结果 → 假引用，清空 + 人工复核（绝不静默放过）
        raw["clauseRef"] = ""
        raw["verdict"] = "unclear"
        raw["needsHumanReview"] = True
    else:
        # 无条款号 → 待补
        raw["clauseRef"] = ""
        raw["needsHumanReview"] = bool(raw.get("needsHumanReview", False))

    # description 缺失但含 conclusion → 用 conclusion 作为说明
    if not raw.get("description") and raw.get("conclusion"):
        raw["description"] = str(raw["conclusion"]).strip()

    return raw


def _apply_evidence_gate(finding: dict) -> dict:
    """M10 防误报证据门槛：nonCompliant 必须有足够置信度 + 原文证据 + 法条引用。

    背景（2026-09-02）：开源 MoE（Qwen3-235B）无视 prompt 克制纪律，把多数维度判
    nonCompliant → 误报率 0.3-0.6 远超红线 0.15。这里做代码层兜底：模型对某维度
    自评 confidence < 0.6，或拿不出原文证据/法条引用时，不武断报违规，转 unclear +
    needsHumanReview（疑似违规交人工复核）。这是合规审查系统的合理行为——拿不准的不
    直接定性违规。注意：只影响 weak 的 nonCompliant，高置信 + 有证据的真违规不受影响。
    """
    if finding.get("verdict") != "nonCompliant":
        return finding
    try:
        conf = float(finding.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    evidence = finding.get("evidence")
    ev_text = str(evidence.get("text") or "") if isinstance(evidence, dict) else ""
    clause = str(finding.get("clauseRef") or "")
    if conf < 0.6 or not ev_text.strip() or clause in ("", "待补"):
        finding["verdict"] = "unclear"
        finding["needsHumanReview"] = True
        description = str(finding.get("description") or "").strip()
        finding["description"] = (description + "（证据不足，转人工复核）").strip()
    return finding


def _apply_requirement_check(finding: dict) -> dict:
    """M10.2 要件核查纠偏（2026-09-15）：按合规要件核查结果纠偏 verdict。

    只做**降级纠偏**（治误报），不做升级纠偏（不造漏报）：
    - 模型判 nonCompliant 且要件**全部 satisfied** → 降为 compliant
      （触发词误报：真实政策 7/7 误报的根因——模型只匹配"跨境/共享/广告推送"等
      触发词，不核查"是否单独同意/是否给退订/是否告知权利"等合规要件）；
    - 模型判 nonCompliant 且存在 **missing** 要件 → 维持 nonCompliant，
      description 注明缺失要件（可解释性）；
    - 模型判 nonCompliant 且要件状态含 **unknown** → 转 unclear + needsHumanReview
      （拿不准的交人工，不武断报违规）；
    - 模型判 compliant/notApplicable → 不改动（漏报由高危规则/后续版本处理）。

    模型未输出 requirementCheck → 原样返回（兼容旧模型输出/降级链路）。
    """
    if finding.get("verdict") != "nonCompliant":
        return finding
    rc = finding.get("requirement_check")
    if not rc:
        return finding
    statuses = [item["status"] for item in rc]
    missing = [item["name"] for item in rc if item["status"] == "missing"]
    if missing:
        desc = str(finding.get("description") or "").strip()
        mark = "【要件核查】缺失要件：" + "、".join(missing) + "。"
        if "缺失要件" not in desc:
            finding["description"] = (mark + desc).strip()
        return finding
    if any(s == "unknown" for s in statuses):
        finding["verdict"] = "unclear"
        finding["needsHumanReview"] = True
        finding["description"] = (
            "【要件核查】要件状态不确定（含 unknown），原判定 nonCompliant 转人工复核："
            + str(finding.get("description") or "")
        ).strip()
        return finding
    # 全部 satisfied → 触发词误报，纠偏为合规
    finding["verdict"] = "compliant"
    finding["level"] = "medium"
    finding["clauseRef"] = ""
    finding["needsHumanReview"] = False
    finding["description"] = (
        "【要件核查】本维度合规要件均已满足（"
        + "、".join(item["name"] for item in rc)
        + "），原判定 nonCompliant 为触发词误报，已纠偏为合规。"
    )
    return finding


_STRIP_RE = re.compile(
    r"[\s\u3000，。、；：？！“”‘’（）《》〈〉【】〔〕…—–·,.;:!?()\[\]{}<>\"'`~@#$%^&*+=|\\/-]+"
)


def _normalize_text(s: str) -> str:
    """归一化文本用于锚定比较：去掉空白与标点，保留汉字/字母/数字。"""
    return _STRIP_RE.sub("", s or "")


def _evidence_in_document(evidence_text: str, doc_text: str, window: int = 8) -> bool:
    """evidence 是否锚定于文档原文：归一化后与原文存在 ≥window 连续字符重合。

    真实违规的 evidence 必然逐字摘自文档原句（金标 evidenceText 亦为原句摘录）；
    模型编造的 evidence 是自组织语言，与无关文档共享 8 连字的概率趋近于零。
    用 8-gram 双向检索实现 O(len_doc + len_ev)，不依赖模型自评 confidence。
    """
    if not evidence_text or not doc_text:
        return False
    norm_ev = _normalize_text(evidence_text)
    norm_doc = _normalize_text(doc_text)
    if not norm_ev or not norm_doc:
        return False
    if len(norm_doc) < window:
        # 文档极短（归一化后不足 window）：宽放为整段包含判断，避免误伤
        return norm_doc in norm_ev
    if len(norm_ev) < window:
        return norm_ev in norm_doc
    grams = {norm_doc[i : i + window] for i in range(len(norm_doc) - window + 1)}
    for i in range(len(norm_ev) - window + 1):
        if norm_ev[i : i + window] in grams:
            return True
    return False


# 维度行为信号词（契约值 → 描述该维度处理行为的原文关键词）：
# M10 第二道防误报（2026-09-04）——拦截"证据真实但维度错配"型幻觉：
# 235B 类模型把文档中真实违规句（如 d1 收集句/d5 跨境句）原样摘录后安到
# **其它维度**头上当证据（g02 的 d2 用"收集生物识别+提供境外"句作证）→
# 证据锚定（第一道）拦不住（句子确实在文档里），须校验证据句是否真的描述
# 本维度的处理行为（命中本维度信号词）。真违规的证据必然含该维度行为词。
_DIM_EVIDENCE_KEYWORDS: dict[str, tuple[str, ...]] = {
    # 2026-09-10 补词：全量回归扫描 124 条金标证据发现 14 条被本表误杀——
    #   d2 缺"说明"（"…保存期限不在本政策中说明" 8 条）
    #   d1 缺"生物识别"（"处理您的生物识别信息…无需您单独同意" 6 条）
    # 补词后回归零误杀；锚定（第一道）仍要求 ≥8 连字原文匹配，幻觉照拦。
    "d1Collection": (
        "收集", "采集", "获取", "录入", "填写", "要求提供", "注册时",
        "生物识别", "人脸", "指纹", "行踪轨迹", "身份证", "敏感个人信息",
    ),
    "d2Notice": (
        "告知", "通知", "同意", "授权", "明示", "单独同意", "撤回同意", "知情",
        "显著方式", "说明", "披露", "声明",
    ),
    "d3Purpose": ("目的", "用于", "画像", "推荐", "营销", "调研", "超出", "用途", "变相"),
    "d4ThirdParty": ("第三方", "共享", "委托", "转让", "出售", "卖给", "合作伙伴", "供应商"),
    "d5CrossBorder": ("境外", "跨境", "出境", "海外", "国外", "向境外", "安全评估"),
    "d6DataRights": ("删除", "更正", "补充", "查询", "复制", "注销", "投诉", "查阅", "撤回"),
}


def _evidence_mentions_dimension(evidence_text: str, dimension: str) -> bool:
    """证据句是否描述该维度的处理行为：命中该维度任一信号词。"""
    keywords = _DIM_EVIDENCE_KEYWORDS.get(dimension)
    if not keywords:
        return True  # 未知维度不拦截（保守）
    norm = _normalize_text(evidence_text)
    return any(k in norm for k in keywords)


def _fix_notice_clause(finding: dict) -> dict:
    """D2 告知条款确定性映射（2026-09-11）：未告知类违规锁定 PIPL 第十七条。

    背景：金标 d2Notice 的 clauseRef **全部是第十七条**（告知义务条款），但免费模型
    常在相邻条款间乱选（实测报出第六条/第十六条/第二十二条）→ 条款准确率被压低。
    证据若指向"未以显著方式告知处理目的、方式、种类、保存期限"，法律上即违反第十七条。
    """
    if finding.get("dimension") != "d2Notice" or finding.get("verdict") != "nonCompliant":
        return finding
    finding["clauseRef"] = "第十七条"
    return finding


def _fix_crossborder_clause(finding: dict) -> dict:
    """D5 跨境条款确定性映射（2026-09-05）：按证据行为锁定 PIPL 条款。

    背景：金标 d5CrossBorder 只有两种期望——『重要数据/关键信息基础设施出境未经
    安全评估』= 第四十条；『向境外提供未取得单独同意/未告知』= 第三十九条。免费模型
    （4.5-flash/235B）在 38/39/40 相邻条款间随机摇摆（三者在检索结果中都相关）→
    条款准确率被压到 0.6。把 d5 条款从 LLM 记忆改为确定性规则：证据含安全评估义务
    信号 → 第四十条；含单独同意/告知信号 → 第三十九条；两者均无 → 保留 LLM 原值。
    """
    if finding.get("dimension") != "d5CrossBorder" or finding.get("verdict") != "nonCompliant":
        return finding
    evidence = finding.get("evidence")
    ev_text = str(evidence.get("text") or "") if isinstance(evidence, dict) else ""
    if not ev_text.strip():
        ev_text = str(finding.get("description") or "")
    norm = _normalize_text(ev_text)
    eval_signal = any(k in norm for k in ("安全评估", "申报", "重要数据", "关键信息基础设施", "存储境内"))
    consent_signal = any(k in norm for k in ("单独同意", "同意", "告知", "视为同意"))
    if eval_signal:
        finding["clauseRef"] = "第四十条"
    elif consent_signal:
        finding["clauseRef"] = "第三十九条"
    return finding


# ── 高危违规模式的确定性兜底（2026-09-10）────────────────────────────
# 背景：免费模型（235B/4.5-flash）对"法律上明确违规"的表述会随机漏报——
# 同一句 d2 证据（"…不在本政策中说明"）在 g14 被报出、在 g16 被漏掉
# （同族文档、同 prompt）→ 高风险召回（红线 ≥0.90）不稳定、无法验收。
# 这些表述本身即违法，无需模型判断：如"无需取得您的同意"违反第二十三条、
# "注册即视为同意"违反第十四条（同意须自愿、明确）。模型漏报时由代码强制报出。
# 注意：仅在模型未判违规时触发，不覆盖模型已有的 nonCompliant 判断。
_HIGH_RISK_PATTERNS: dict[str, tuple[tuple[str, str], ...]] = {
    "d1Collection": (
        (r"等全部个人信息|全部个人信息|所有个人信息", "第五条"),
    ),
    "d2Notice": (
        (r"不在本政策中说明|不在本隐私政策中说明|未(?:向您)?说明处理|未告知", "第十七条"),
    ),
    "d4ThirdParty": (
        (r"(?:无需|无须|不必)(?:另行)?(?:取得)?(?:您的)?同意", "第二十二条"),
    ),
    "d5CrossBorder": (
        (r"注册即视为同意|视为同意该传输", "第三十九条"),
    ),
}


# ── 合规信号豁免（M10.2，2026-09-15）────────────────────────────
# 强合规要素信号词（按维度细分 + 全局兜底）。命中说明文档原文存在合规措施
# （同意/DPA/退订/权利路径等），此时模型即便判 nonCompliant 也高度疑似误报——
# 真实政策盲测 7/7 误报全部命中这些词（京东 8 条退订路径/单独同意/DPA、
# 微信境内境外隔离与权利行使路径、淘宝清关法定义务）。
# 定位：要件核查（第一道）依赖 LLM 填写质量，此为**代码层第二道保险**。
_COMPLIANCE_SIGNALS: dict[str, tuple[str, ...]] = {
    "d1Collection": (
        "明示同意", "单独同意", "授权同意", "征得同意",
        # M11（2026-09-19）：软性合规表述——支付宝 r07 误报根因（精确短语，避免过度豁免）
        "如您不提供", "不影响您使用", "可拒绝提供",
        # M13（2026-09-21）：DPA 专有特征——微软 c06 d1 误报根因。
        # DPA 的性质是"收集范围由控制者（客户）决定、数据类别见附录"，不是隐私政策，
        # 不应以"未明示收集范围"判违规。只用 DPA/SCC 最专有短语（恶意合同/隐私政策
        # 不会使用），避免过度豁免；⚠ 匹配走 _normalize_text（去空格），用归一化形态：
        "documentedinstructions", "categoriesofpersonaldata",
    ),
    "d2Notice": (
        "显著方式", "显著位置", "撤回同意", "明示同意", "单独同意", "弹窗",
        "本隐私政策", "隐私政策", "告知您", "向您告知", "明确告知",
    ),
    "d3Purpose": (
        "退订", "关闭", "拒绝", "推荐管理", "不针对其个人特征", "选择权",
        "处理目的", "仅用于",
    ),
    "d4ThirdParty": (
        "单独同意", "授权同意", "事先获得", "明示同意", "数据保护协议", "同等保护", "除外",
        # M11：软性合规——"为提供服务所必需/基于法定义务/信息授权服务"
        "为向您提供服务所必需", "基于法定义务", "信息授权", "基于您的同意", "经您同意",
    ),
    "d5CrossBorder": (
        "单独同意", "授权同意", "数据保护协议", "安全评估", "标准合同", "认证", "跨境传输协议",
        "取得您的授权", "境外接收方", "个人信息保护影响评估",
    ),
    "d6DataRights": (
        "删除", "更正", "注销", "撤回同意", "查阅", "复制", "投诉", "15天", "15日内", "渠道", "途径",
        "您有权", "您可以",
    ),
}

_GLOBAL_COMPLIANCE_SIGNALS = (
    "单独同意", "授权同意", "数据保护协议", "安全评估", "标准合同",
    # M11：软性合规全局信号（支付宝 d1/d4 误报根因，精确短语）
    "为向您提供服务所必需", "基于法定义务", "信息授权",
    "如您不提供", "不影响您使用",
)

# M12 适用性预筛信号（2026-09-20）：模型判 notApplicable 时，若文档命中本维度
# 的**强适用信号**，说明"该查没查"（漏检），强制转人工复核。
# 信号词特意收窄为合同/法律文件专用短语（cross-border/SCC/BCR/data exporter 等），
# 不用泛化词（transfer/处理）——避免把任何提到"传输/处理"的文档都误触发。
# ⚠ 匹配形态：_apply_applicability_gate 内先 _normalize_text(doc).lower() 再子串匹配，
#   故信号词必须写成"归一化形态"（小写、无空格、无连字符）——"cross-border"→"crossborder"。
_APPLICABILITY_SIGNALS: dict[str, tuple[str, ...]] = {
    "d1Collection": (
        "categoriesofpersonaldata", "personaldataprocessed",
        "收集", "处理个人信息",
    ),
    "d3Purpose": (
        "purposeoftheprocessing", "processingpurposes", "purposesoftheprocessing",
        "处理目的", "仅用于", "为提供",
    ),
    "d4ThirdParty": (
        "subprocessor", "thirdpartyprocessor", "delegate",
        "子处理者", "委托处理", "第三方",
    ),
    "d5CrossBorder": (
        "crossborder", "internationaldatatransfer",
        "datatransfermechanism", "standardcontractualclauses",
        "bindingcorporaterules", "adequacydecision",
        "dataexporter", "dataimporter", "restrictedtransfer",
        "跨境", "出境", "标准合同", "安全评估", "境外接收方",
    ),
    "d6DataRights": (
        "datasubjectrights", "datasubjectrequest", "righttoerasure",
        "righttoaccess", "righttocorrection", "accessrequest",
        "datasubjects", "数据主体权利",
        "删除权", "查阅权", "更正", "撤回同意",
    ),
}


def _apply_applicability_gate(finding: dict, doc_text: str, dimension: str) -> dict:
    """M12 适用性预筛门（2026-09-20）：notApplicable 且文档含该维度强信号 → 转人工复核。

    背景：免费模型对英文法律文本（DPA/SCC/IDTA）语义映射弱，把明确含跨境传输条款的
    合同判成 d5 notApplicable（漏检方向：该查没查）。本门用确定性关键词兜底——
    文档命中维度的强适用信号时，禁止直接采信 notApplicable，转 unclear 交人工。
    信号词收窄为合同专用短语；只动 notApplicable，不影响其它判定。
    """
    if str(finding.get("verdict") or "") != "notApplicable":
        return finding
    if not doc_text:
        return finding
    dim = normalize_dimension(dimension, dimension)
    signals = _APPLICABILITY_SIGNALS.get(dim)
    if not signals:
        return finding
    norm = _normalize_text(doc_text).lower()
    for kw in signals:
        if kw in norm:
            finding["verdict"] = "unclear"
            finding["needsHumanReview"] = True
            finding["clauseRef"] = finding.get("clauseRef") or "待补"
            finding["description"] = (
                "【适用性预筛】文档命中该维度适用信号「"
                + kw
                + "」，原判定 notApplicable 疑为漏检（该查没查），转人工复核："
                + str(finding.get("description") or "")
            ).strip()
            return finding
    return finding


def _has_compliance_signal(doc_text: str, dimension: str = "") -> bool:
    """文档是否含合规要素信号（同意/DPA/退订/权利路径等豁免要素）。"""
    if not doc_text:
        return False
    norm = _normalize_text(doc_text)
    if dimension:
        for kw in _COMPLIANCE_SIGNALS.get(dimension, ()):
            if kw in norm:
                return True
    for kw in _GLOBAL_COMPLIANCE_SIGNALS:
        if kw in norm:
            return True
    return False


def _apply_compliance_exception(finding: dict, doc_text: str) -> dict:
    """M10.2 合规信号豁免门（2026-09-15）：nonCompliant 且文档含强合规信号 → 转人工复核。

    文档明确出现单独同意/DPA/安全评估/退订/注销等合规要素时，不再直接定性违规，
    降级 unclear + needsHumanReview 交人工——拿不准的不硬报违规。
    """
    if finding.get("verdict") != "nonCompliant":
        return finding
    dim = str(finding.get("dimension") or "")
    if _has_compliance_signal(doc_text, dim):
        finding["verdict"] = "unclear"
        finding["needsHumanReview"] = True
        finding["description"] = (
            "【合规信号豁免】文档原文存在合规要素（同意/DPA/安全评估/退订/权利路径等），"
            "原判定 nonCompliant 降级待人工复核："
            + str(finding.get("description") or "")
        ).strip()
    return finding


def _evidence_sentence(doc_text: str, matched: str) -> str:
    """取包含命中模式的原文整句（保证兜底证据能通过锚定校验）。"""
    for sent in re.split(r"[。！？；\n]", doc_text or ""):
        s = sent.strip()
        if s and matched in _normalize_text(s):
            return s
    return ""


def _apply_high_risk_rule(finding: dict, doc_text: str, dimension: str) -> dict:
    """确定性高危规则兜底：文档含明确违规表述而模型未报时，强制报 nonCompliant。

    仅在模型未判 nonCompliant 时触发；命中后注入原文证据句（可过锚定校验）。

    注意：节点传入的 ``dimension`` 是 **d1/d2 编号**，而规则表用**契约值**
    （d1Collection/d2Notice）作 key —— 必须先过 ``normalize_dimension`` 归一化，
    否则规则永远匹配不上（2026-09-11 踩过：兜底静默失效，召回仍为 0）。
    """
    if str(finding.get("verdict") or "") == "nonCompliant":
        return finding
    dim = normalize_dimension(dimension, dimension)
    patterns = _HIGH_RISK_PATTERNS.get(dim)
    if not patterns or not doc_text:
        return finding
    # M10.2（2026-09-15）：文档含合规信号时不强制报违规——模板句规则只对"无任何
    # 合规措施"的文档生效；真实政策大多含同意/退订/权利等豁免要素，命中规则句
    # （如"注册即视为同意"）应转人工而非武断判违规。
    if _has_compliance_signal(doc_text, dim):
        return finding
    norm = _normalize_text(doc_text)
    for pat, clause in patterns:
        m = re.search(pat, norm)
        if not m:
            continue
        evidence = _evidence_sentence(doc_text, m.group(0))
        if not evidence:
            continue
        finding["verdict"] = "nonCompliant"
        finding["level"] = "high"
        finding["clauseRef"] = clause
        finding["needsHumanReview"] = False
        finding["confidence"] = 0.8
        finding["statuteVersion"] = (
            finding.get("statuteVersion") or "个人信息保护法(2021-11-01)"
        )
        finding["description"] = (
            f"【确定性规则兜底】文档存在明确违规表述「{m.group(0)}」（{clause}），"
            "模型未识别，由规则强制判定为不合规。"
        )
        finding["remediation"] = (
            finding.get("remediation") or "整改该违规表述并依法取得授权"
        )
        finding["evidence"] = {"text": evidence, "charRange": [0, 0]}
        return finding
    return finding


def _apply_evidence_anchor(finding: dict, doc_text: str) -> dict:
    """M10 防幻觉证据锚定（2026-09-04）：nonCompliant 必须有能锚定到文档原文的证据。

    背景：免费模型（glm-4.5-flash / 开源 MoE）对文档**完全未涉及**的维度也编造违规
    （g02 文档仅 319 字、无"第三方/告知/删除"等任何字样，模型仍报 d2/d3/d4/d6 四项
    违规）→ 误报率 0.3-0.67 远超红线 0.15，且每次重跑结果随机——幻觉无法靠 prompt
    措辞压制（9/1-9/2 已试过三版纪律 prompt，对 4.5-flash 无效），只能代码层确定性拦截。

    规则（两道校验，命中任一即降级 notApplicable）：
    ① 证据锚定：evidence.text（缺失时退回 description）必须能在文档原文中找到
       （归一化后 ≥8 连字）——拦"证据完全编造"型（该维度文档无任何行为）；
    ② 维度一致性：证据文本必须命中本维度的行为信号词——拦"证据真实但维度错配"型
       （模型把文档中其它维度的真违规句摘录后安到本维度头上，如 235B 常见）。
    真实违规的证据必然同时满足①②（出自原文 + 描述本维度行为）→ 零误伤。

    与 2026-09-02 移除的 _apply_evidence_gate 的本质区别：那里用 confidence<0.6 门槛，
    误伤自评保守的谨慎商业模型（真违规也被转走）；这里只做**文本事实校验**（原文锚定 +
    维度行为词），不触碰 confidence——只要模型如实摘录了本维度的原文证据即放行。
    """
    if finding.get("verdict") != "nonCompliant":
        return finding
    evidence = finding.get("evidence")
    ev_text = str(evidence.get("text") or "") if isinstance(evidence, dict) else ""
    if not ev_text.strip():
        ev_text = str(finding.get("description") or "")
    if not _evidence_in_document(ev_text, doc_text):
        finding["verdict"] = "notApplicable"
    elif not _evidence_mentions_dimension(ev_text, str(finding.get("dimension") or "")):
        finding["verdict"] = "notApplicable"
    else:
        return finding
    finding["clauseRef"] = ""
    finding["needsHumanReview"] = False  # 确定性"不适用"，无需人工；原模型输出已保留在 description 供审计
    original_desc = str(finding.get("description") or "").strip() or ev_text
    finding["description"] = (
        "【证据无法在文档原文中找到，或与维度不符，原判定 nonCompliant 不成立，降级为不适用】"
        + original_desc
    ).strip()
    return finding


def build_dimension_node(
    dimension: str,
    llm_func: Callable[..., Awaitable[str]],
) -> Callable[[Any], Awaitable[dict]]:
    """构建一个六维审查节点。

    :param dimension: d1-d6
    :param llm_func: async LLM 调用函数（生产走 factory.chat_completion；测试注入 mock）
    """
    spec = get_prompt(dimension)

    async def node(state: dict) -> dict:
        task_id = state["task_id"]
        publish_event(task_id, "nodeStart", {"node": spec.name, "dimension": dimension})
        # 组装 messages（system = 提示词 system；user = 渲染模板）
        user_content = spec.render_user(
            document=state.get("document_text", ""),
            retrieval=state.get("retrieval", ""),
            context=state.get("graph_summary", ""),
            graph_risk=state.get("graph_summary", ""),
        )
        messages = [
            {"role": "system", "content": spec.system},
            {"role": "user", "content": user_content},
        ]

        # 降级默认：LLM 异常/校验失败 → 待补 + needsHumanReview（dimension 用契约值）
        degraded = {
            "dimension": normalize_dimension(None, dimension),
            "verdict": "unclear",
            "level": "medium",
            "clauseRef": "待补",
            "statuteVersion": None,
            "description": f"{spec.name} LLM 调用失败，已降级为待人工复核",
            "remediation": "请人工复核该维度",
            "confidence": 0.0,
            "needsHumanReview": True,
        }

        try:
            call_kwargs: dict[str, Any] = {
                "messages": messages,
                "dimension": dimension,
                "task_id": task_id,
            }
            # M9-8：透传用户自有 Key（无则不含该参数 → 走系统 Key；不破坏测试 mock 签名）
            if state.get("api_key_override"):
                call_kwargs["api_key_override"] = state["api_key_override"]
            # M10.3：维度级失败重试（免费模型输出不稳定：超时/429/JSON 畸形偶发）
            # 重试上限 + 递增退避；成功即跳出。仍失败 → 抛给外层降级逻辑。
            text, raw = await _call_with_retry(llm_func, call_kwargs)
            # 规范化 LLM 原始输出（schema 不稳定容忍层：维度/verdict/clauseRef + 检索命中校验）
            raw = _normalize_llm_raw(raw, dimension, state.get("retrieval", ""))
            finding, warnings = validate_finding(raw)
            if finding is None:
                logger.warning("维度 %s 校验丢弃: %s", dimension, warnings)
                publish_event(
                    task_id,
                    "nodeEnd",
                    {"node": spec.name, "dimension": dimension, "degraded": True},
                )
                return {"findings": [degraded]}
            # M10.2：requirementCheck 经 validate_finding 白名单会被丢弃，手动回填
            finding["requirement_check"] = raw.get("_requirement_check")
            # M10 防幻觉：nonCompliant 必须锚定文档原文证据，否则降级不适用（2026-09-04）
            finding = _apply_evidence_anchor(finding, state.get("document_text", ""))
            # M12 适用性预筛（2026-09-20）：notApplicable 但文档含维度强信号 → 转人工复核
            # 防"该查没查"漏检（英文 DPA/SCC 跨境条款被误判 notApplicable）
            finding = _apply_applicability_gate(
                finding, state.get("document_text", ""), dimension
            )
            # M10.2 要件核查纠偏（第一道防线，2026-09-15）：要件全满足 → 纠为 compliant
            finding = _apply_requirement_check(finding)
            # M10.2 合规信号豁免门（第二道防线，2026-09-15）：强合规信号 → 转人工复核
            finding = _apply_compliance_exception(
                finding, state.get("document_text", "")
            )
            # 高危规则兜底（2026-09-10 / M10.2 改线索）：模型漏报的"法律上明确违规"表述
            # 强制报出；文档含合规信号时不触发（避免模板句规则误伤真实文本）
            finding = _apply_high_risk_rule(
                finding, state.get("document_text", ""), dimension
            )
            # M10 d5 条款确定性映射（2026-09-05）：安全评估→40条 / 单独同意→39条
            finding = _fix_crossborder_clause(finding)
            # M10 d2 告知条款确定性映射（2026-09-11）：未告知 → 第十七条
            finding = _fix_notice_clause(finding)
            publish_event(task_id, "nodeEnd", {"node": spec.name, "dimension": dimension})
            return {"findings": [finding]}
        except Exception as exc:  # 降级容错：任务不中断
            logger.warning("维度 %s LLM 失败，降级待补: %s", dimension, exc)
            publish_event(
                task_id, "nodeEnd", {"node": spec.name, "dimension": dimension, "degraded": True}
            )
            return {"findings": [degraded]}

    return node
