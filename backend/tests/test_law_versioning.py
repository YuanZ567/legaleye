"""M2-4 验收测试：法条版本化（新增版本而非覆盖 + effectiveDate 生效 + 旧报告追溯）。

覆盖：
- 新版本入库：同条款不同 version 共存，不覆盖旧版本；
- effectiveDate 生效：`get_active_article` 按查询时点返回对应生效版本；
- 旧报告版本追溯：`get_article_version` 按报告锁定的 version 精确取回，不受新版本影响；
- 无命中返回 None（不编造）。
"""

from collections.abc import Generator
from datetime import date

import pytest
from app.knowledge.law_service import (
    get_active_article,
    get_article_version,
    ingest_laws,
)
from app.models import SQLModel
from app.models.law_baseline import LawBaseline
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestingSession() as session:
        yield session
    SQLModel.metadata.drop_all(engine)


def _law(*, version: str, effective: date, text: str) -> dict:
    return {
        "statute": "个人信息保护法",
        "article_no": "第十三条",
        "article_text": text,
        "version": version,
        "effective_date": effective,
        "source": "官方公布文本",
    }


# ── 新版本入库：共存不覆盖 ──


def test_new_version_coexist_not_overwrite(db: Session):
    """同条款新版本入库：与旧版本共存，不覆盖。"""
    v1 = _law(version="laws-v1.0-20260812", effective=date(2021, 11, 1), text="旧版本条文")
    v2 = _law(version="laws-v1.1-20270101", effective=date(2027, 1, 1), text="新版本条文")

    ingest_laws(db, [v1])
    ingest_laws(db, [v2])

    rows = db.scalars(
        select(LawBaseline).where(
            LawBaseline.statute == "个人信息保护法", LawBaseline.article_no == "第十三条"
        )
    ).all()
    assert len(rows) == 2  # 新旧版本共存
    versions = {r.version: r.article_text for r in rows}
    assert versions["laws-v1.0-20260812"] == "旧版本条文"
    assert versions["laws-v1.1-20270101"] == "新版本条文"  # 旧版本未被覆盖


# ── effectiveDate 生效 ──


def test_active_article_effective_date(db: Session):
    """get_active_article 按查询时点返回对应生效版本。"""
    v1 = _law(version="laws-v1.0-20260812", effective=date(2021, 11, 1), text="旧条文")
    v2 = _law(version="laws-v1.1-20270101", effective=date(2027, 1, 1), text="新条文")
    ingest_laws(db, [v1, v2])

    # 新版本生效日之前：应返回旧版本
    active_before = get_active_article(
        db=db, statute="个人信息保护法", article_no="第十三条", on_date=date(2026, 12, 31)
    )
    assert active_before is not None and active_before.version == "laws-v1.0-20260812"

    # 新版本生效日当天/之后：应返回新版本
    active_after = get_active_article(
        db=db, statute="个人信息保护法", article_no="第十三条", on_date=date(2027, 1, 1)
    )
    assert active_after is not None and active_after.version == "laws-v1.1-20270101"


def test_active_article_no_hit_returns_none(db: Session):
    """生效日前无任何版本（或条款不存在）→ None（不编造）。"""
    v1 = _law(version="laws-v1.0-20260812", effective=date(2021, 11, 1), text="条文")
    ingest_laws(db, [v1])
    # 生效日之前无版本
    assert (
        get_active_article(
            db=db, statute="个人信息保护法", article_no="第十三条", on_date=date(2020, 1, 1)
        )
        is None
    )
    # 条款不存在
    assert (
        get_active_article(
            db=db, statute="不存在的法", article_no="第一条", on_date=date(2030, 1, 1)
        )
        is None
    )


# ── 旧报告版本追溯 ──


def test_article_version_traceability(db: Session):
    """get_article_version 按报告锁定的 version 精确取回，即使有新版本也不受影响。"""
    v1 = _law(version="laws-v1.0-20260812", effective=date(2021, 11, 1), text="报告引用时的条文")
    v2 = _law(version="laws-v1.1-20270101", effective=date(2027, 1, 1), text="后来修订的条文")
    ingest_laws(db, [v1, v2])

    # 报告锁定旧版本 v1.0：即使新版本已入库，追溯仍返回 v1.0 原文
    traced = get_article_version(
        db=db, statute="个人信息保护法", article_no="第十三条", version="laws-v1.0-20260812"
    )
    assert traced is not None and traced.article_text == "报告引用时的条文"

    # 追溯不存在的版本 → None
    assert (
        get_article_version(
            db=db, statute="个人信息保护法", article_no="第十三条", version="laws-v9.9"
        )
        is None
    )


def test_version_dedup_no_duplicate(db: Session):
    """同版本重复入库仍幂等：总数不增。"""
    v1 = _law(version="laws-v1.0-20260812", effective=date(2021, 11, 1), text="条文")
    ingest_laws(db, [v1])
    ingest_laws(db, [v1])
    count = db.scalar(select(func.count()).select_from(LawBaseline))
    assert count == 1
