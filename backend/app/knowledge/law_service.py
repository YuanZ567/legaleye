"""法条基线入库服务（M2-3）：幂等 upsert。

纪律：
- 幂等：按唯一约束 `statute+article_no+version` 判重，已存在则跳过，重复运行不产生重复记录；
- 版本化：修订新增 version（不同 version 共存），不覆盖旧版本；
- 检索无命中返回空，不编造（供 M2-6 检索用）；
- 本模块只做落库，法规数据由 ingest 脚本提供，不含版权文本。
"""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models.law_baseline import LawBaseline
from app.services.embedding_service import embed_text


def add_law(
    *,
    db: Session,
    statute: str,
    article_no: str,
    article_text: str,
    version: str | None,
    effective_date: date,
    source: str,
) -> LawBaseline:
    """添加法条（M9-7 admin）：生成 embedding 后入库。

    - 去重：statute + article_no + version 已存在 → 抛 409；
    - embedding 生成失败 → 抛 500（不静默降级）；
    - version 缺省用 config.laws_baseline_version（报告锁存版本，禁硬编码）。
    """
    final_version = version or get_settings().laws_baseline_version
    exists = db.execute(
        select(LawBaseline.id).where(
            LawBaseline.statute == statute,
            LawBaseline.article_no == article_no,
            LawBaseline.version == final_version,
        )
    ).first()
    if exists is not None:
        raise DomainError(
            f"该条款已存在（{statute} {article_no} v{final_version}）",
            code="law_duplicate",
            status_code=409,
        )

    law = LawBaseline(
        statute=statute,
        article_no=article_no,
        article_text=article_text,
        version=final_version,
        effective_date=effective_date,
        source=source,
    )
    db.add(law)
    db.flush()  # 取 id

    # embedding 必须有向量（M9-7 红线：不静默降级）
    law.embedding = embed_text(article_text)
    db.commit()
    db.refresh(law)
    return law


def upsert_law(
    *,
    db: Session,
    statute: str,
    article_no: str,
    article_text: str,
    version: str,
    effective_date: date,
    source: str,
) -> bool:
    """幂等插入一条法条。

    若 (statute, article_no, version) 已存在则跳过（返回 False，未插入）；
    否则插入（返回 True）。embedding 由后续 M2-5 语义索引回填。
    """
    exists = db.execute(
        select(LawBaseline.id).where(
            LawBaseline.statute == statute,
            LawBaseline.article_no == article_no,
            LawBaseline.version == version,
        )
    ).first()
    if exists is not None:
        return False  # 幂等：已存在，跳过

    db.add(
        LawBaseline(
            statute=statute,
            article_no=article_no,
            article_text=article_text,
            version=version,
            effective_date=effective_date,
            source=source,
        )
    )
    db.commit()
    return True


def get_active_article(
    *,
    db: Session,
    statute: str,
    article_no: str,
    on_date: date,
) -> LawBaseline | None:
    """返回指定日期时点"生效"的法条（effectiveDate <= on_date 且版本最新）。

    用于检索当前生效版本（M2-6）。无命中返回 None（不编造）。
    """
    rows = (
        db.execute(
            select(LawBaseline).where(
                LawBaseline.statute == statute,
                LawBaseline.article_no == article_no,
                LawBaseline.effective_date <= on_date,
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return None
    # 取 effective_date 最晚（即最新生效）的一条
    return max(rows, key=lambda r: r.effective_date)  # noqa: B023


def get_article_version(
    *,
    db: Session,
    statute: str,
    article_no: str,
    version: str,
) -> LawBaseline | None:
    """按精确版本取回法条（旧报告版本追溯）。

    即使已有新版本，也严格按报告锁定的 version 返回该版本原文，保证追溯一致。
    无命中返回 None（不编造）。
    """
    return db.execute(
        select(LawBaseline).where(
            LawBaseline.statute == statute,
            LawBaseline.article_no == article_no,
            LawBaseline.version == version,
        )
    ).scalar_one_or_none()


def list_laws(
    *,
    db: Session,
    statute: str | None = None,
    version: str | None = None,
) -> list[LawBaseline]:
    """列出法条基线（GET /knowledge/laws 服务）；支持 statute/version 过滤。

    未指定 version 时，返回所有版本（由前端/调用方决定是否只取生效版）。
    """
    stmt = select(LawBaseline)
    if statute:
        stmt = stmt.where(LawBaseline.statute == statute)
    if version:
        stmt = stmt.where(LawBaseline.version == version)
    return list(db.scalars(stmt).all())


def ingest_laws(db: Session, laws: list[dict[str, Any]]) -> dict[str, int]:
    """批量幂等入库。

    :param laws: 每条含 statute/article_no/article_text/version/effective_date/source。
    :return: {"inserted": N, "skipped": M}。
    """
    inserted = 0
    skipped = 0
    for law in laws:
        ok = upsert_law(
            db=db,
            statute=law["statute"],
            article_no=law["article_no"],
            article_text=law["article_text"],
            version=law["version"],
            effective_date=law["effective_date"],
            source=law["source"],
        )
        if ok:
            inserted += 1
        else:
            skipped += 1
    return {"inserted": inserted, "skipped": skipped}
