"""M2-3 验收测试：ingest_laws 幂等入库。

- 首次运行全部插入；
- 重复运行不产生重复记录（inserted=0, skipped=总数）；
- 版本化：不同 version 共存。
用内存 SQLite 验证服务层逻辑（真实验证见 scripts/ingest_laws.py + PG）。
"""

from collections.abc import Generator
from datetime import date

import pytest
from app.knowledge.law_service import ingest_laws
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


_LAWS = [
    {
        "statute": "个人信息保护法",
        "article_no": "第一条",
        "article_text": "为了保护个人信息权益，制定本法。",
        "version": "laws-v1.0-20260812",
        "effective_date": date(2021, 11, 1),
        "source": "官方公布文本",
    },
    {
        "statute": "数据安全法",
        "article_no": "第五条",
        "article_text": "国家建立数据分类分级保护制度。",
        "version": "laws-v1.0-20260812",
        "effective_date": date(2021, 9, 1),
        "source": "官方公布文本",
    },
]


def test_ingest_first_run_all_inserted(db: Session):
    """首次运行：全部插入，无跳过。"""
    result = ingest_laws(db, _LAWS)
    assert result == {"inserted": 2, "skipped": 0}
    count = db.scalar(select(func.count()).select_from(LawBaseline))
    assert count == 2


def test_ingest_idempotent_second_run(db: Session):
    """重复运行：不产生重复记录（inserted=0, skipped=总数）。"""
    ingest_laws(db, _LAWS)
    result = ingest_laws(db, _LAWS)
    assert result == {"inserted": 0, "skipped": 2}
    count = db.scalar(select(func.count()).select_from(LawBaseline))
    assert count == 2  # 未重复插入


def test_ingest_version_coexist(db: Session):
    """不同 version 的同条款可共存（版本化不覆盖）。"""
    ingest_laws(db, _LAWS)
    new_version = [{**law, "version": "laws-v1.1-20270101"} for law in _LAWS]
    result = ingest_laws(db, new_version)
    assert result == {"inserted": 2, "skipped": 0}
    count = db.scalar(select(func.count()).select_from(LawBaseline))
    assert count == 4  # 旧版 2 + 新版 2


def test_ingest_gbt_placeholder(db: Session):
    """GB/T 待补占位：不包含版权文本。"""
    laws = [
        {
            "statute": "GB/T 35273-2020",
            "article_no": "待补",
            "article_text": "待补：版权文本待用户提供后入库。",
            "version": "laws-v1.0-20260812",
            "effective_date": date(2020, 10, 1),
            "source": "待用户提供版权文本",
        }
    ]
    ingest_laws(db, laws)
    row = db.scalar(select(LawBaseline).where(LawBaseline.statute == "GB/T 35273-2020"))
    assert row is not None
    assert "待补" in row.article_text
