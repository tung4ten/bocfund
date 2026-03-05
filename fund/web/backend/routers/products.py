from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_db
from ..schemas import CompareResponse, HistoryPoint, ProductHistory

router = APIRouter(prefix="/api/products", tags=["products"])


def _resolve_product_name(db: Session, code: str, candidate_name: str | None) -> str:
    """若候选名称为空，从全量记录中查找该产品最新的非空名称。"""
    if candidate_name and candidate_name.strip():
        return candidate_name.strip()
    row = db.execute(
        text(
            "SELECT product_name FROM boc_nav_records "
            "WHERE product_code = :code AND product_name IS NOT NULL AND TRIM(product_name) != '' "
            "ORDER BY as_of_date DESC LIMIT 1"
        ),
        {"code": code},
    ).fetchone()
    return row[0].strip() if row and row[0] else code  # 实在找不到就用代码本身


@router.get("/{code}/history", response_model=ProductHistory)
def get_product_history(
    code: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """返回单个产品最近 N 天的历史数据。"""
    sql = text(
        "WITH latest AS ("
        "  SELECT MAX(as_of_date) AS max_date FROM boc_nav_records WHERE product_code = :code"
        ") "
        "SELECT product_code, product_name, as_of_date, "
        "       annualized_7d_or_growth, income_per_10k, cumulative_nav, daily_growth_rate "
        "FROM boc_nav_records "
        "WHERE product_code = :code "
        "  AND as_of_date >= date((SELECT max_date FROM latest), '-' || :days || ' days') "
        "ORDER BY as_of_date"
    )
    rows = db.execute(sql, {"code": code, "days": days}).fetchall()

    candidate_name = rows[0][1] if rows else None
    name = _resolve_product_name(db, code, candidate_name)
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

    return ProductHistory(product_code=code, product_name=name, history=history)


@router.get("/compare", response_model=CompareResponse)
def compare_products(
    codes: str = Query(..., description="逗号分隔的产品代码列表"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """多产品历史数据对比。时间窗口以各产品最新可用日期的公共参照日为锚点，减少节假日缺数据。"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return CompareResponse(series=[])

    placeholders = ",".join([f":c{i}" for i in range(len(code_list))])
    params = {f"c{i}": c for i, c in enumerate(code_list)}
    params["days"] = days

    # 各产品取最新日期，再取 MIN 作为公共参照日，确保所有产品在该窗口内均有数据
    sql = text(
        f"WITH LatestPerProduct AS ("
        f"  SELECT product_code, MAX(as_of_date) AS max_date "
        f"  FROM boc_nav_records WHERE product_code IN ({placeholders}) "
        f"  GROUP BY product_code"
        f"), "
        f"RefDate AS ("
        f"  SELECT MIN(max_date) AS ref_date FROM LatestPerProduct"
        f") "
        f"SELECT n.product_code, n.product_name, n.as_of_date, "
        f"       n.annualized_7d_or_growth, n.income_per_10k, n.cumulative_nav, n.daily_growth_rate "
        f"FROM boc_nav_records n "
        f"CROSS JOIN RefDate "
        f"WHERE n.product_code IN ({placeholders}) "
        f"  AND n.as_of_date >= date((SELECT ref_date FROM RefDate), '-' || :days || ' days') "
        f"  AND n.as_of_date <= (SELECT ref_date FROM RefDate) "
        f"ORDER BY n.product_code, n.as_of_date"
    )

    rows = db.execute(sql, params).fetchall()

    from collections import OrderedDict

    grouped: OrderedDict[str, ProductHistory] = OrderedDict()
    for r in rows:
        code = r[0]
        if code not in grouped:
            name = _resolve_product_name(db, code, r[1])
            grouped[code] = ProductHistory(
                product_code=code, product_name=name, history=[]
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

    # 拉取风险等级与封闭期限并填充
    risk_rows = db.execute(
        text(
            f"SELECT product_code, risk_level FROM product_risk_levels "
            f"WHERE product_code IN ({placeholders})"
        ),
        params,
    ).fetchall()
    risk_map = {row[0]: row[1] for row in risk_rows}
    try:
        lp_rows = db.execute(
            text(
                f"SELECT product_code, lockup_period_text, lockup_period_days "
                f"FROM product_lockup_periods WHERE product_code IN ({placeholders})"
            ),
            params,
        ).fetchall()
        lockup_map = {r[0]: (r[1], r[2]) for r in lp_rows}
    except Exception:
        lockup_map = {}
    for s in grouped.values():
        s.risk_level = risk_map.get(s.product_code)  # type: ignore
        if s.product_code in lockup_map:
            s.lockup_period_text, s.lockup_period_days = lockup_map[s.product_code]
            s.lockup_period_source = "manual"

    # 按请求顺序排列
    order = {c: i for i, c in enumerate(code_list)}
    series = sorted(grouped.values(), key=lambda s: order.get(s.product_code, 999))

    return CompareResponse(series=series)
