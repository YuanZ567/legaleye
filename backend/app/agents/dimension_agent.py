"""六维审查节点（M4-4）：真实 LLM 调用（经 llm/factory）+ finding 强校验 + 降级。

流程：
1. 读取 prompts 维度提示词（集中管理，禁止散落）；
2. 经 llm/factory.chat_completion 调用（唯一入口，自动记账 LLMCallRecord）；
3. 输出过 schemas/validators.validate_finding 强校验（clauseRef 正则/confidence 钳制/枚举丢弃）；
4. 校验失败/LLM 异常 → 降级"待补 + needsHumanReview=true"（任务不中断）。

llm_func 可注入（测试 mock），默认走 factory（生产真实调用）。
"""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.sse import publish_event
from app.prompts import get_prompt
from app.schemas.validators import validate_finding

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    """从 LLM 输出提取 JSON（容忍 markdown 代码块包裹）。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # 去掉 ```json ... ``` 包裹
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


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


def _normalize_llm_raw(raw: dict, fallback_dim: str, retrieval: str = "") -> dict:
    """规范化 LLM 原始输出（schema 不稳定的容忍层）。

    - dimension：归一化到契约值；
    - verdict 缺失但含 conclusion → 按语义推断（不合规/合规/部分/不适用）；
    - clauseRef 清洗 + **检索命中校验**（红线：禁无引用结论）——LLM 输出的条款号
      必须在本轮检索结果中，否则强制清空 + needsHumanReview + verdict=unclear
      （绝不静默放过"假引用"）；
    - level 缺失默认 medium。
    """
    import re

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
            text = await llm_func(**call_kwargs)
            raw = _extract_json(text)
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
            publish_event(task_id, "nodeEnd", {"node": spec.name, "dimension": dimension})
            return {"findings": [finding]}
        except Exception as exc:  # 降级容错：任务不中断
            logger.warning("维度 %s LLM 失败，降级待补: %s", dimension, exc)
            publish_event(
                task_id, "nodeEnd", {"node": spec.name, "dimension": dimension, "degraded": True}
            )
            return {"findings": [degraded]}

    return node
