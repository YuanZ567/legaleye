"""M2-1 验收测试：LawBaseline 模型契约 + 唯一约束 + 版本化。

- 字段对齐 DATA_CONTRACT 4.10（statute/article_no/article_text/effective_date/version/source）；
- 唯一约束 statute+article_no+version（TODO 不允许破坏）：同条款同版本重复插入抛异常；
- 版本化：不同 version 可共存（修订新增版本而非覆盖）。

SQLite 内存库验证（pgvector Vector 列兼容）；真实验证见迁移 + PG 检查。
"""

from collections.abc import Generator
from datetime import date

import pytest
from app.models import SQLModel
from app.models.law_baseline import LawBaseline
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
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


def _make_law(version: str = "laws-v1.0-20260811", article_no: str = "第一条") -> LawBaseline:
    return LawBaseline(
        statute="个人信息保护法",
        article_no=article_no,
        article_text="处理个人信息应当遵循合法、正当、必要原则。",
        version=version,
        effective_date=date(2021, 11, 1),
        source="官方公布文本",
    )


def test_model_fields_match_contract(db: Session):
    """模型字段对齐 DATA_CONTRACT 4.10 LawBaseline。"""
    cols = {c.name for c in SQLModel.metadata.tables["law_baselines"].columns}
    assert {"statute", "article_no", "article_text", "version", "effective_date", "source"} <= cols


def test_insert_and_read(db: Session):
    """插入条款并可回读。"""
    law = _make_law()
    db.add(law)
    db.commit()
    db.refresh(law)
    assert law.id is not None
    assert law.statute == "个人信息保护法"
    assert law.effective_date == date(2021, 11, 1)
    assert law.version == "laws-v1.0-20260811"


def test_unique_constraint_same_version(db: Session):
    """同 statute+article_no+version 重复插入 → IntegrityError（不允许破坏）。"""
    db.add(_make_law())
    db.commit()
    with pytest.raises(IntegrityError):
        db.add(_make_law())  # 同版本同条款 → 唯一约束冲突
        db.commit()


def test_versioned_coexist(db: Session):
    """不同 version 的同一条款可共存（修订新增版本而非覆盖）。"""
    db.add(_make_law(version="laws-v1.0-20260811"))
    db.add(_make_law(version="laws-v1.1-20270101"))
    db.commit()

    count = (
        db.query(LawBaseline)
        .filter(LawBaseline.statute == "个人信息保护法", LawBaseline.article_no == "第一条")
        .count()
    )
    assert count == 2
