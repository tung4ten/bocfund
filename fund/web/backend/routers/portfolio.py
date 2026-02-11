from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_db, load_portfolio_codes
from ..schemas import (
    CompareResponse,
    HistoryPoint,
    PortfolioResponse,
    ProductHistory,
    ProductSnapshot,
)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioResponse)
def get_portfolio(db: Session = Depends(get_db)):
    """返回持仓产品的最新指标。"""
    codes = load_portfolio_codes()
    if not codes:
        return PortfolioResponse(products=[])

    placeholders = ",".join([f":c{i}" for i in range(len(codes))])
    params = {f"c{i}": c for i, c in enumerate(codes)}

    # 取每个产品最新一条记录
    sql = text(
        f"SELECT r.product_code, r.product_name, r.unit_nav, r.cumulative_nav, "
        f"       r.income_per_10k, r.annualized_7d_or_growth, r.daily_growth_rate, r.as_of_date "
        f"FROM boc_nav_records r "
        f"INNER JOIN ("
        f"  SELECT product_code, MAX(as_of_date) AS max_date "
        f"  FROM boc_nav_records "
        f"  WHERE product_code IN ({placeholders}) "
        f"  GROUP BY product_code"
        f") latest ON r.product_code = latest.product_code AND r.as_of_date = latest.max_date"
    )

    rows = db.execute(sql, params).fetchall()

    # 按 portfolio.json 中的顺序排序
    order = {c: i for i, c in enumerate(codes)}
    items = sorted(
        [
            ProductSnapshot(
                product_code=r[0],
                product_name=r[1] or "",
                unit_nav=r[2],
                cumulative_nav=r[3],
                income_per_10k=r[4],
                annualized_7d=r[5],
                daily_growth_rate=r[6],
                as_of_date=r[7],
            )
            for r in rows
        ],
        key=lambda p: order.get(p.product_code, 999),
    )

    return PortfolioResponse(products=items)


@router.get("/history", response_model=CompareResponse)
def get_portfolio_history(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """返回持仓产品最近 N 天的历史七日年化数据（用于趋势图）。"""
    codes = load_portfolio_codes()
    if not codes:
        return CompareResponse(series=[])

    placeholders = ",".join([f":c{i}" for i in range(len(codes))])
    params = {f"c{i}": c for i, c in enumerate(codes)}
    params["days"] = days

    sql = text(
        f"SELECT product_code, product_name, as_of_date, "
        f"       annualized_7d_or_growth, income_per_10k, cumulative_nav, daily_growth_rate "
        f"FROM boc_nav_records "
        f"WHERE product_code IN ({placeholders}) "
        f"  AND as_of_date >= date('now', '-' || :days || ' days') "
        f"ORDER BY product_code, as_of_date"
    )

    rows = db.execute(sql, params).fetchall()

    # 按产品分组
    from collections import OrderedDict

    grouped: OrderedDict[str, ProductHistory] = OrderedDict()
    for r in rows:
        code = r[0]
        if code not in grouped:
            grouped[code] = ProductHistory(
                product_code=code, product_name=r[1] or "", history=[]
            )
        grouped[code].history.append(
            HistoryPoint(
                as_of_date=r[2],
                annualized_7d=r[3],
                income_per_10k=r[4],
                cumulative_nav=r[5],
                daily_growth_rate=r[6],
            )
        )

    # 按 portfolio.json 中的顺序排序
    order = {c: i for i, c in enumerate(codes)}
    series = sorted(grouped.values(), key=lambda s: order.get(s.product_code, 999))

    return CompareResponse(series=series)
