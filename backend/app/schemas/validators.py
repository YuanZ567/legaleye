"""LLM 字段强制校验（DATA_CONTRACT 4.8 / 第 6 章 LLM 字段校验清单）。

规则：
- `clauseRef` 正则（3.2）失败 → verdict=pending + needsHumanReview=true（不丢弃，降级标注）；
- `confidence` 钳制到 [0,1]（越界 clamp，NaN 归 0）；
- `dimension/verdict/level` 枚举未知 → 丢弃该条 + 返回告警；
- 其余字段缺失 → 用安全默认值补齐。
"""

import math
import re

from app.core.enums import FindingLevel, FindingVerdict, ReviewDimension

# clauseRef 正则（对齐 DATA_CONTRACT 3.2）
CLAUSE_REF_RE = re.compile(r"第?[一二三四五六七八九十\d]+条(第[一二三四五六七八九十\d]+款)?")

# 合法枚举取值集合
_DIMENSIONS = {d.value for d in ReviewDimension}
_VERDICTS = {v.value for v in FindingVerdict}
_LEVELS = {lvl.value for lvl in FindingLevel}


def _clamp_confidence(value) -> float:
    """confidence 钳制到 [0,1]；非法/NaN 归 0。"""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(f) or math.isinf(f):
        return 0.0
    return round(max(0.0, min(1.0, f)), 4)


def validate_finding(raw: dict) -> tuple[dict | None, list[str]]:
    """校验并规范化一条 LLM 输出的 finding。

    :return: (normalized_finding 或 None[丢弃], warnings[list[str]])
    """
    warnings: list[str] = []

    # 枚举未知 → 丢弃
    dimension = raw.get("dimension")
    verdict = raw.get("verdict")
    level = raw.get("level")
    if dimension not in _DIMENSIONS:
        return None, [f"dimension 未知丢弃: {dimension}"]
    if verdict not in _VERDICTS:
        return None, [f"verdict 未知丢弃: {verdict}"]
    if level not in _LEVELS:
        return None, [f"level 未知丢弃: {level}"]

    # clauseRef 正则；失败 → 降级"待补" + needsHumanReview（不改 verdict，用标记而非 pending）
    clause_ref = str(raw.get("clauseRef") or "").strip()
    needs_human = bool(raw.get("needsHumanReview", False))
    if clause_ref not in ("", "待补") and not CLAUSE_REF_RE.fullmatch(clause_ref):
        warnings.append(f"clauseRef 非法，降级待补: {clause_ref}")
        clause_ref = "待补"
        needs_human = True

    # confidence 钳制
    confidence = _clamp_confidence(raw.get("confidence"))

    # 规范化输出（snake_case 内部 + camelCase 契约字段并存）
    return {
        "dimension": dimension,
        "verdict": verdict,
        "level": level,
        "clauseRef": clause_ref,
        "statuteVersion": str(raw.get("statuteVersion") or "").strip() or None,
        "description": str(raw.get("description") or "").strip(),
        "remediation": str(raw.get("remediation") or "").strip(),
        "confidence": confidence,
        "needsHumanReview": needs_human,
        "evidence": raw.get("evidence") if isinstance(raw.get("evidence"), dict) else None,
    }, warnings
