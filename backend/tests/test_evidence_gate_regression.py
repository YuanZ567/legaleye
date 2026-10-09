"""证据闸门回归测试。

回归语料换为两层：
1. **真实证据基线**：22 份真实文档盲测中通过闸门的 28 条证据
   （tests/fixtures/real_evidence_baseline.json，源自 docs/blind_eval_results.json），
   断言锚定 + 维度一致性**永远通过**——防止词表/校验逻辑改动造成真实分布回退；
2. **精选违规证据夹具**：覆盖历史上被误杀关键词的 7 条违规措辞
   （tests/fixtures/golden_violation_evidence.curated.json），
   断言维度一致性**永远通过**——防止"修一处、错一片"（d2"说明"、d1"生物识别"复发）。

与 test_dimension_agent.py 的分工：那里测节点行为（mock LLM），这里测校验器本身
对真实语料的普适性。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.dimension_agent import (
    _evidence_in_document,
    _evidence_mentions_dimension,
)

ROOT = Path(__file__).resolve().parents[2]
REAL_DIR = ROOT / "data" / "real"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASELINE = FIXTURES / "real_evidence_baseline.json"
CURATED = FIXTURES / "golden_violation_evidence.curated.json"

pytestmark = pytest.mark.skipif(
    not REAL_DIR.exists(), reason="缺少 data/real 真实语料（CI 精简环境跳过）"
)


def _load_fixture(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["cases"] if isinstance(data, dict) else data


def test_real_evidence_baseline_never_gated() -> None:
    """真实文档盲测中通过闸门的证据，必须在锚定 + 维度一致性上持续通过。

    任何一条从"通过"变"误杀"，都说明词表或校验逻辑发生了回退。
    """
    cases = _load_fixture(BASELINE)
    assert len(cases) >= 20, "真实证据基线加载异常（应 ≥20 条）"
    kills: list[str] = []
    for c in cases:
        doc_path = REAL_DIR / c["file"]
        if not doc_path.exists():
            continue
        doc = doc_path.read_text(encoding="utf-8")
        if not _evidence_in_document(c["evidence"], doc):
            kills.append(f"{c['file']}/{c['dimension']}: 锚定失败: {c['evidence'][:60]}")
        elif not _evidence_mentions_dimension(c["evidence"], c["dimension"]):
            kills.append(f"{c['file']}/{c['dimension']}: 维度误杀: {c['evidence'][:60]}")
    assert not kills, (
        f"{len(kills)}/{len(cases)} 条真实证据被证据闸门误杀（词表或校验逻辑回退）：\n  "
        + "\n  ".join(kills)
    )


def test_curated_violation_evidence_never_dim_killed() -> None:
    """历史误杀关键词（d1 生物识别 / d2 说明 / d5 安全评估 等）的违规证据措辞，
    必须全部通过维度一致性校验——防止词表覆盖回退导致真实违规被漏检。"""
    cases = _load_fixture(CURATED)
    assert len(cases) >= 6, "精选违规证据夹具加载异常"
    kills: list[str] = []
    covered: set[str] = set()
    for c in cases:
        covered.add(c["keyword"])
        if not _evidence_mentions_dimension(c["evidence"], c["dimension"]):
            kills.append(f"{c['dimension']}/{c['keyword']}: {c['evidence'][:60]}")
    # 历史误杀关键词必须全部在覆盖清单内（新增维度词时在此补充）
    for kw in ("生物识别", "敏感个人信息", "说明", "安全评估", "出境"):
        assert kw in covered, f"精选夹具缺少历史误杀关键词「{kw}」的覆盖样本"
    assert not kills, (
        f"{len(kills)}/{len(cases)} 条违规证据措辞被维度校验误杀：\n  " + "\n  ".join(kills)
    )


# ── 高危规则兜底（2026-09-11）──────────────────────────────────────────
# 回归背景：`_apply_high_risk_rule` 的规则表用契约值（d2Notice）作 key，而节点
# 传入的是编号（d2）→ 兜底**静默失效**、召回仍为 0（全量评估跑完才发现）。
# 本测试直接以"编号维度"调用，确保归一化生效。
_GATE_CASES = [
    ("d1", "d1Collection", "为提供服务，我们会收集您的手机号、身份证号码、账号、位置信息等全部个人信息。", "第五条"),
    ("d2", "d2Notice", "我们可能对您的个人信息进行必要处理，处理的具体种类、目的与保存期限不在本政策中说明。", "第十七条"),
    ("d4", "d4ThirdParty", "我们会将您的信息共享给合作营销商以开展推广活动，无需另行取得您的同意。", "第二十二条"),
    ("d5", "d5CrossBorder", "为提升服务，我们会将您的个人信息跨境提供给境外的云服务商，您注册即视为同意该传输。", "第三十九条"),
]


@pytest.mark.parametrize("dim_code,contract,doc,clause", _GATE_CASES)
def test_high_risk_rule_triggers_with_numeric_dimension(
    dim_code: str, contract: str, doc: str, clause: str
) -> None:
    """模型漏报（verdict=unclear/compliant）时，规则必须按编号维度兜底报出。"""
    from app.agents.dimension_agent import _apply_high_risk_rule

    for weak_verdict in ("unclear", "compliant", "notApplicable"):
        finding = {
            "dimension": contract,
            "verdict": weak_verdict,
            "level": "medium",
            "clauseRef": "",
            "description": "模型认为无问题",
            "evidence": {"text": "", "charRange": [0, 0]},
        }
        out = _apply_high_risk_rule(finding, doc, dim_code)  # ← 编号维度
        assert out["verdict"] == "nonCompliant", (
            f"{dim_code}/{weak_verdict} 规则兜底未触发（key 归一化失效？）"
        )
        assert out["level"] == "high"
        assert out["clauseRef"] == clause
        assert out["evidence"]["text"], "兜底必须注入原文证据句"


def test_high_risk_rule_does_not_override_model_judgment() -> None:
    """模型已判 nonCompliant 时不干预；文档无违规表述时不误报。"""
    from app.agents.dimension_agent import _apply_high_risk_rule

    already = {"dimension": "d2Notice", "verdict": "nonCompliant", "clauseRef": "第十七条"}
    assert _apply_high_risk_rule(dict(already), "随意文本", "d2")["clauseRef"] == "第十七条"

    clean = {"dimension": "d2Notice", "verdict": "compliant", "level": "low"}
    out = _apply_high_risk_rule(
        dict(clean), "我们已以显著方式向您告知处理个人信息的种类、目的、方式与保存期限。", "d2"
    )
    assert out["verdict"] == "compliant", "合规文档被规则误报"
