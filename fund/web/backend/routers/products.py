from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_db
from ..schemas import CompareResponse, HistoryPoint, ProductHistory

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/{code}/history", response_model=ProductHistory)
def get_product_history(
    code: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """返回单个产品最近 N 天的历史数据。"""
    sql = text(
        "SELECT product_code, product_name, as_of_date, "
        "       annualized_7d_or_growth, income_per_10k, cumulative_nav, daily_growth_rate "
        "FROM boc_nav_records "
        "WHERE product_code = :code "
        "  AND as_of_date >= date('now', '-' || :days || ' days') "
        "ORDER BY as_of_date"
    )
    rows = db.execute(sql, {"code": code, "days": days}).fetchall()

    name = rows[0][1] if rows else ""
    history = [
        HistoryPoint(
            as_of_date=r[2],
            annualized_7d=r[3],
            income_per_10k=r[4],
            cumulative_nav=r[5],
            daily_growth_rate=r[6],
        )
        for r in rows
    ]

    return ProductHistory(product_code=code, product_name=name or "", history=history)


@router.get("/compare", response_model=CompareResponse)
def compare_products(
    codes: str = Query(..., description="逗号分隔的产品代码列表"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """多产品历史数据对比。"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return CompareResponse(series=[])

    placeholders = ",".join([f":c{i}" for i in range(len(code_list))])
    params = {f"c{i}": c for i, c in enumerate(code_list)}
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

    # 按请求顺序排列
    order = {c: i for i, c in enumerate(code_list)}
    series = sorted(grouped.values(), key=lambda s: order.get(s.product_code, 999))

    return CompareResponse(series=series)
