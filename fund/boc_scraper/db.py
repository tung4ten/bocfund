from __future__ import annotations

import os
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Mapping, Optional

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Numeric,
    String,
    create_engine,
    func,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


DEFAULT_DB_RELATIVE_PATH = "fund/data/boc_nav.sqlite3"


class Base(DeclarativeBase):
    pass


class BocNavRecord(Base):
    __tablename__ = "boc_nav_records"

    # 以产品代码 + 截止日期作为唯一键
    product_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)

    product_name: Mapped[str] = mapped_column(String(255))
    unit_nav: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    cumulative_nav: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    income_per_10k: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    annualized_7d_or_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    daily_growth_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)

    source_page_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)


def _ensure_parent_dir(db_path: str) -> None:
    p = Path(db_path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)


def _normalize_db_url(db_path: Optional[str]) -> str:
    if db_path and (db_path.startswith("sqlite:///") or db_path.startswith("sqlite://")):
        return db_path
    use_path = db_path or os.environ.get("BOC_DB_PATH") or DEFAULT_DB_RELATIVE_PATH
    _ensure_parent_dir(use_path)
    # Windows 路径转为 SQLAlchemy 兼容 URL
    abs_path = str(Path(use_path).resolve())
    return f"sqlite:///{abs_path}"


def get_engine(db_path: Optional[str] = None):
    engine_url = _normalize_db_url(db_path)
    return create_engine(engine_url, future=True)


def create_tables(engine) -> None:
    Base.metadata.create_all(engine)


def upsert_records(session: Session, records: Iterable[Mapping]) -> int:
    """
    基于 (product_code, as_of_date) 进行幂等写入（存在则更新，不存在则插入）
    返回受影响的记录数（近似，以提交的记录数为准）
    """
    to_list: List[Mapping] = list(records)
    if not to_list:
        return 0
    BATCH_SIZE = 200
    total = 0
    for i in range(0, len(to_list), BATCH_SIZE):
        batch = to_list[i : i + BATCH_SIZE]
        insert_stmt = sqlite_insert(BocNavRecord).values(batch)
        update_cols = {
            "product_name": insert_stmt.excluded.product_name,
            "unit_nav": insert_stmt.excluded.unit_nav,
            "cumulative_nav": insert_stmt.excluded.cumulative_nav,
            "income_per_10k": insert_stmt.excluded.income_per_10k,
            "annualized_7d_or_growth": insert_stmt.excluded.annualized_7d_or_growth,
            "daily_growth_rate": insert_stmt.excluded.daily_growth_rate,
            "source_page_url": insert_stmt.excluded.source_page_url,
            "updated_at": func.now(),
        }
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[BocNavRecord.product_code, BocNavRecord.as_of_date],
            set_=update_cols,
        )
        session.execute(upsert_stmt)
        total += len(batch)
    return total


