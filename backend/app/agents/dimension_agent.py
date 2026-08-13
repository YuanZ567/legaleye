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

        # 降级默认：LLM 异常/校验失败 → 待补 + needsHumanReview
        degraded = {
            "dimension": dimension,
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
            text = await llm_func(messages=messages, dimension=dimension, task_id=task_id)
            raw = _extract_json(text)
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
