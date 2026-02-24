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
    """返回持仓产品的最新指标（包含 portfolio.json 配置的和数据库中有交易记录的产品）。"""
    # 1. 从配置文件读取
    config_codes = set(load_portfolio_codes())
    
    # 2. 从交易记录读取
    try:
        tx_rows = db.execute(text("SELECT DISTINCT product_code FROM portfolio_transactions")).fetchall()
        tx_codes = {r[0] for r in tx_rows}
    except Exception:
        # 表可能不存在
        tx_codes = set()
        
    # 3. 合并去重
    codes = list(config_codes | tx_codes)
    
    if not codes:
        return PortfolioResponse(products=[])

    placeholders = ",".join([f":c{i}" for i in range(len(codes))])
    params = {f"c{i}": c for i, c in enumerate(codes)}

    # 取每个产品最新8条记录（通过窗口函数），用于计算7日年化
    sql = text(
        f"""
        WITH Ranked AS (
            SELECT product_code, product_name, unit_nav, cumulative_nav,
                   income_per_10k, annualized_7d_or_growth, daily_growth_rate, as_of_date,
                   julianday(as_of_date) as jd,
                   ROW_NUMBER() OVER (PARTITION BY product_code ORDER BY as_of_date DESC) as rn
            FROM boc_nav_records
            WHERE product_code IN ({placeholders})
        )
        SELECT * FROM Ranked WHERE rn <= 10
        """
    )

    all_rows = db.execute(sql, params).fetchall()

    # Group by product_code
    grouped = {}
    for r in all_rows:
        pc = r[0]
        if pc not in grouped:
            grouped[pc] = []
        grouped[pc].append(r)
    
    # 按 portfolio.json 中的顺序优先排序，其余排后面
    json_order = {c: i for i, c in enumerate(load_portfolio_codes())} 
    
    items = []
    for code in codes:
        if code not in grouped: continue
        
        recs = grouped[code]
        # recs[0] is latest (rn=1)
        curr = recs[0]
        # curr tuple index: 
        # 0:code, 1:name, 2:unit, 3:cum, 4:inc, 5:ann7d, 6:day_growth, 7:date, 8:jd, 9:rn
        
        prev = recs[1] if len(recs) > 1 else None
        
        # 1. Calculate Day NAV Change
        day_change = None
        if prev:
            # Priority: cumulative_nav diff, else unit_nav diff
            if curr[3] is not None and prev[3] is not None:
                day_change = float(curr[3]) - float(prev[3])
            elif curr[2] is not None and prev[2] is not None:
                day_change = float(curr[2]) - float(prev[2])
        
        # 2. Calculate Annualized 7D if missing
        ann_7d = curr[5]
        ann_source = "direct" if ann_7d is not None else None
        
        if ann_7d is None and curr[3] is not None:
            # Find a record closest to 7 days ago (between 4 and 10 days ago)
            curr_jd = curr[8]
            best_past = None
            min_diff = 999
            
            for past_rec in recs[1:]:
                past_jd = past_rec[8]
                days_diff = curr_jd - past_jd
                if 4 <= days_diff <= 25 and past_rec[3] is not None:
                    diff_from_7 = abs(days_diff - 7)
                    if diff_from_7 < min_diff:
                        min_diff = diff_from_7
                        best_past = past_rec
                        best_days_diff = days_diff
            
            if best_past:
                past_cum = float(best_past[3])
                curr_cum = float(curr[3])
                if past_cum > 0:
                    ann_7d = (curr_cum - past_cum) / past_cum * (365.0 / best_days_diff) * 100
                    ann_source = "calculated"
                    
        # 3. Simulate Income Per 10k for Net Value products (if missing)
        # Definition: Profit for 10,000 units.
        # If unit_nav ~ 1.0, then 10,000 units ~ 10,000 RMB principal.
        inc_10k = curr[4]
        if (inc_10k is None or inc_10k == 0) and day_change is not None:
             # Use the calculated day_change (which is per unit) * 10000
             inc_10k = day_change * 10000.0

        items.append(ProductSnapshot(
            product_code=curr[0],
            product_name=curr[1] or "",
            unit_nav=curr[2],
            cumulative_nav=curr[3],
            income_per_10k=inc_10k,
            annualized_7d=ann_7d,
            daily_growth_rate=curr[6],
            as_of_date=curr[7],
            day_nav_change=day_change,
            annualized_7d_source=ann_source
        ))
        
    items.sort(key=lambda p: json_order.get(p.product_code, 9999))

    return PortfolioResponse(products=items)


@router.get("/history", response_model=CompareResponse)
def get_portfolio_history(
    days: int = Query(30, ge=1, le=36500),
    db: Session = Depends(get_db),
):
    """返回持仓产品最近 N 天的历史七日年化数据（用于趋势图）。"""
    # 1. 从配置文件读取
    config_codes = set(load_portfolio_codes())
    
    # 2. 从交易记录读取
    try:
        tx_rows = db.execute(text("SELECT DISTINCT product_code FROM portfolio_transactions")).fetchall()
        tx_codes = {r[0] for r in tx_rows}
    except Exception:
        tx_codes = set()
        
    # 3. 合并去重
    codes = list(config_codes | tx_codes)
    
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
