from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_db
from ..schemas import ProductSnapshot, RankingResponse

router = APIRouter(prefix="/api/ranking", tags=["ranking"])

# 正常交易日七日年化记录数通常在 350-370 之间
MIN_RECORDS_THRESHOLD = 300


def _find_reference_date(db: Session) -> str | None:
    """找到最近一个数据充足的日期。

    优先取七日年化直接记录数 >= 阈值的日期，如果没有则退回到
    总记录数最大的最近日期。
    """
    row = db.execute(
        text(
            "SELECT as_of_date "
            "FROM boc_nav_records "
            "WHERE annualized_7d_or_growth IS NOT NULL AND annualized_7d_or_growth > 0 "
            "GROUP BY as_of_date "
            "HAVING COUNT(*) >= :threshold "
            "ORDER BY as_of_date DESC "
            "LIMIT 1"
        ),
        {"threshold": MIN_RECORDS_THRESHOLD},
    ).fetchone()

    if row and row[0]:
        return row[0]

    # 退回方案
    row = db.execute(
        text(
            "SELECT MAX(as_of_date) FROM boc_nav_records "
            "WHERE annualized_7d_or_growth IS NOT NULL AND annualized_7d_or_growth > 0"
        )
    ).fetchone()
    return row[0] if row else None


@router.get("/top50", response_model=RankingResponse)
def get_top50(
    limit: int = Query(50, ge=1, le=500),
    risk: Optional[str] = Query(None, description="按风险等级筛选，如 R1, R2, R3, R4，逗号分隔可多选"),
    db: Session = Depends(get_db),
):
    """返回最新数据充足日期的七日年化收益率 Top N 产品。

    数据来源：
    1. 现金管理类产品：直接使用 annualized_7d_or_growth 字段（source=direct）
    2. 净值型产品：通过 (最新累计净值 - 约7天前累计净值) / 约7天前累计净值 * (365/实际天数) * 100 计算（source=calculated）

    风险等级来源：中银理财官网 (bocwm.cn) API + 产品名称关键词推断。
    """

    latest_date = _find_reference_date(db)
    if not latest_date:
        return RankingResponse(as_of_date="1970-01-01", items=[])

    # 解析风险等级筛选参数
    risk_filter_clause = ""
    if risk:
        risk_levels = [r.strip().upper() for r in risk.split(",") if r.strip()]
        if risk_levels:
            placeholders = ",".join([f"'{r}'" for r in risk_levels])
            risk_filter_clause = f"AND rl.risk_level IN ({placeholders})"

    # 用一条 CTE 查询合并两类产品，并 JOIN 风险等级表
    sql = text(f"""
        WITH
        -- 当前日期的所有产品
        current_data AS (
            SELECT product_code, product_name, unit_nav, cumulative_nav,
                   income_per_10k, annualized_7d_or_growth, daily_growth_rate, as_of_date
            FROM boc_nav_records
            WHERE as_of_date = :ref_date
        ),
        -- 净值型产品的历史净值候选（距 ref_date 4~10 天内，取最接近 7 天的记录）
        past_candidates AS (
            SELECT n.product_code,
                   n.cumulative_nav                                       AS past_nav,
                   n.as_of_date                                           AS past_date,
                   julianday(:ref_date) - julianday(n.as_of_date)         AS days_diff,
                   ROW_NUMBER() OVER (
                       PARTITION BY n.product_code
                       ORDER BY ABS(julianday(:ref_date) - julianday(n.as_of_date) - 7)
                   ) AS rn
            FROM boc_nav_records n
            WHERE n.as_of_date BETWEEN date(:ref_date, '-10 days') AND date(:ref_date, '-4 days')
              AND n.cumulative_nav IS NOT NULL
              AND n.cumulative_nav > 0
        ),
        past_data AS (
            SELECT product_code, past_nav, past_date, days_diff
            FROM past_candidates
            WHERE rn = 1
        ),
        -- 合并：直接值 + 计算值
        merged AS (
            SELECT
                c.product_code,
                c.product_name,
                c.unit_nav,
                c.cumulative_nav,
                c.income_per_10k,
                CASE
                    WHEN c.annualized_7d_or_growth IS NOT NULL
                        THEN c.annualized_7d_or_growth
                    WHEN p.past_nav IS NOT NULL
                         AND c.cumulative_nav IS NOT NULL
                         AND c.cumulative_nav != 1.0
                         AND p.past_nav > 0
                         AND p.days_diff > 0
                        THEN ROUND(
                            (c.cumulative_nav - p.past_nav) / p.past_nav
                            * (365.0 / p.days_diff) * 100,
                            4
                        )
                    ELSE NULL
                END AS effective_7d,
                c.daily_growth_rate,
                c.as_of_date,
                CASE
                    WHEN c.annualized_7d_or_growth IS NOT NULL THEN 'direct'
                    WHEN p.past_nav IS NOT NULL THEN 'calculated'
                    ELSE NULL
                END AS source
            FROM current_data c
            LEFT JOIN past_data p ON c.product_code = p.product_code
        )
        SELECT m.product_code, m.product_name, m.unit_nav, m.cumulative_nav,
               m.income_per_10k, m.effective_7d, m.daily_growth_rate, m.as_of_date,
               m.source, rl.risk_level, rl.risk_label
        FROM merged m
        LEFT JOIN product_risk_levels rl ON m.product_code = rl.product_code
        WHERE m.effective_7d IS NOT NULL AND m.effective_7d > 0
        {risk_filter_clause}
        ORDER BY m.effective_7d DESC
        LIMIT :lim
    """)

    rows = db.execute(sql, {"ref_date": latest_date, "lim": limit}).fetchall()

    items = [
        ProductSnapshot(
            product_code=r[0],
            product_name=r[1] or "",
            unit_nav=r[2],
            cumulative_nav=r[3],
            income_per_10k=r[4],
            annualized_7d=r[5],
            daily_growth_rate=r[6],
            as_of_date=r[7],
            annualized_7d_source=r[8],
            risk_level=r[9],
            risk_label=r[10],
        )
        for r in rows
    ]

    return RankingResponse(as_of_date=latest_date, items=items)
