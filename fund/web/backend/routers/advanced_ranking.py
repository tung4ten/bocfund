from __future__ import annotations

from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..config import get_db
from ..schemas import ProductSnapshot
from ....boc_scraper.db import BocNavRecord

router = APIRouter(
    prefix="/api/ranking",
    tags=["ranking"],
)

def calculate_annualized_return(
    start_nav: Decimal | None,
    end_nav: Decimal | None,
    days: int,
) -> Decimal | None:
    """根据期初和期末净值计算年化回报率"""
    if start_nav is None or end_nav is None or start_nav <= 0 or days <= 0:
        return None
    try:
        annualized_return = (end_nav / start_nav) ** (Decimal(365) / Decimal(days)) - 1
        return annualized_return * 100
    except Exception:
        return None

@router.get("/advanced", response_model=List[ProductSnapshot])
def get_advanced_ranking(
    time_period_days: int = Query(
        90, description="计算收益率的时间周期（天）", ge=7, le=365 * 5
    ),
    limit: int = Query(10000, description="返回的记录数", ge=1, le=10000),
    db: Session = Depends(get_db),
):
    latest_records_sq = (
        select(
            BocNavRecord.product_code,
            func.max(BocNavRecord.as_of_date).label("latest_date"),
        )
        .group_by(BocNavRecord.product_code)
        .subquery("latest_records_sq")
    )

    latest_records = (
        select(BocNavRecord)
        .join(
            latest_records_sq,
            (BocNavRecord.product_code == latest_records_sq.c.product_code)
            & (BocNavRecord.as_of_date == latest_records_sq.c.latest_date),
        )
        .subquery("latest_records")
    )

    start_candidates = (
        select(
            BocNavRecord.product_code,
            BocNavRecord.as_of_date.label("start_date"),
            func.coalesce(BocNavRecord.cumulative_nav, BocNavRecord.unit_nav).label(
                "start_nav"
            ),
            func.abs(
                func.julianday(BocNavRecord.as_of_date)
                - func.julianday(
                    func.date(
                        latest_records_sq.c.latest_date,
                        f"-{time_period_days} days",
                    )
                )
            ).label("days_gap"),
            func.row_number()
            .over(
                partition_by=BocNavRecord.product_code,
                order_by=func.abs(
                    func.julianday(BocNavRecord.as_of_date)
                    - func.julianday(
                        func.date(
                            latest_records_sq.c.latest_date,
                            f"-{time_period_days} days",
                        )
                    )
                ),
            )
            .label("rn"),
        )
        .join(
            latest_records_sq,
            BocNavRecord.product_code == latest_records_sq.c.product_code,
        )
        .where(BocNavRecord.as_of_date < latest_records_sq.c.latest_date)
        .where(func.coalesce(BocNavRecord.cumulative_nav, BocNavRecord.unit_nav) > 0)
        .subquery("start_candidates")
    )

    start_records = (
        select(
            start_candidates.c.product_code,
            start_candidates.c.start_nav,
            start_candidates.c.start_date,
        )
        .where(start_candidates.c.rn == 1)
        .subquery("start_records")
    )

    stmt = (
        select(
            latest_records,
            start_records.c.start_nav,
            start_records.c.start_date,
        )
        .join(start_records, latest_records.c.product_code == start_records.c.product_code)
    )

    results = []
    rows = db.execute(stmt).fetchall()
    
    for row in rows:
        record_data = row._asdict()
        latest_record_data = {k: record_data[k] for k in latest_records.c.keys()}
        
        start_nav = record_data.get("start_nav")
        end_nav = latest_record_data.get("cumulative_nav") or latest_record_data.get(
            "unit_nav"
        )
        start_d = record_data.get("start_date")
        end_d = latest_record_data.get("as_of_date")

        if not all([start_nav, end_nav, start_d, end_d]):
            continue

        actual_days = (end_d - start_d).days
        annualized_return = calculate_annualized_return(start_nav, end_nav, actual_days)

        if annualized_return is not None and actual_days > 0:
            snapshot = ProductSnapshot(
                product_code=latest_record_data["product_code"],
                product_name=latest_record_data["product_name"],
                as_of_date=latest_record_data["as_of_date"],
                unit_nav=latest_record_data.get("unit_nav"),
                cumulative_nav=end_nav,
                income_per_10k=latest_record_data.get("income_per_10k"),
                annualized_7d=annualized_return,
                daily_growth_rate=latest_record_data.get("daily_growth_rate"),
                period_days=actual_days,
                risk_level=None,
                annualized_7d_source="calculated",
            )
            results.append(snapshot)

    if results:
        codes = [item.product_code for item in results]
        placeholders = ",".join([f":c{i}" for i in range(len(codes))])
        params = {f"c{i}": code for i, code in enumerate(codes)}
        rows = db.execute(
            text(
                f"SELECT product_code, risk_level, risk_label "
                f"FROM product_risk_levels WHERE product_code IN ({placeholders})"
            ),
            params,
        ).fetchall()
        risk_map = {r[0]: (r[1], r[2]) for r in rows}
        for item in results:
            if item.product_code in risk_map:
                item.risk_level, item.risk_label = risk_map[item.product_code]

    results.sort(key=lambda x: x.annualized_7d or 0, reverse=True)

    return results[:limit]
