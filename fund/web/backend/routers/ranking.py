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
    """返回最新七日年化收益率 Top N 产品。

    规则：
    - 不要求“今天必须有净值”；
    - 每个产品都基于其“最新可用日期”参与排行；
    - 若无直接七日年化，使用最近约 7 天净值按年化公式计算。
    """

    # 风险筛选（参数化）
    risk_filter_clause = ""
    params: dict[str, object] = {"lim": limit}
    if risk:
        risk_levels = [r.strip().upper() for r in risk.split(",") if r.strip()]
        valid_levels = [r for r in risk_levels if r in {"R1", "R2", "R3", "R4", "R5"}]
        include_undefined = "UNDEFINED" in risk_levels

        normal_clause = ""
        if valid_levels:
            placeholders = []
            for idx, level in enumerate(valid_levels):
                key = f"risk_{idx}"
                placeholders.append(f":{key}")
                params[key] = level
            normal_clause = f"rl.risk_level IN ({','.join(placeholders)})"

        undefined_clause = "(rl.risk_level IS NULL OR TRIM(rl.risk_level) = '')"

        if normal_clause and include_undefined:
            risk_filter_clause = f" AND ({normal_clause} OR {undefined_clause}) "
        elif normal_clause:
            risk_filter_clause = f" AND {normal_clause} "
        elif include_undefined:
            risk_filter_clause = f" AND {undefined_clause} "

    sql = text(
        f"""
        WITH
        LatestDates AS (
            SELECT product_code, MAX(as_of_date) AS max_date
            FROM boc_nav_records
            GROUP BY product_code
        ),
        TargetProducts AS (
            SELECT n.product_code,
                   n.product_name,
                   n.unit_nav,
                   n.cumulative_nav,
                   n.income_per_10k,
                   n.annualized_7d_or_growth,
                   n.daily_growth_rate,
                   n.as_of_date
            FROM boc_nav_records n
            JOIN LatestDates ld
              ON n.product_code = ld.product_code
             AND n.as_of_date = ld.max_date
        ),
        past_candidates AS (
            SELECT tp.product_code,
                   COALESCE(n.cumulative_nav, n.unit_nav)             AS past_nav,
                   n.as_of_date                                       AS past_date,
                   julianday(tp.as_of_date) - julianday(n.as_of_date) AS days_diff,
                   ROW_NUMBER() OVER (
                       PARTITION BY tp.product_code
                       ORDER BY ABS(julianday(tp.as_of_date) - julianday(n.as_of_date) - 7)
                   ) AS rn
            FROM TargetProducts tp
            JOIN boc_nav_records n
              ON tp.product_code = n.product_code
            WHERE n.as_of_date BETWEEN date(tp.as_of_date, '-25 days') AND date(tp.as_of_date, '-4 days')
              AND COALESCE(n.cumulative_nav, n.unit_nav) IS NOT NULL
              AND COALESCE(n.cumulative_nav, n.unit_nav) > 0
        ),
        past_data AS (
            SELECT product_code, past_nav, past_date, days_diff
            FROM past_candidates
            WHERE rn = 1
        ),
        merged AS (
            SELECT
                tp.product_code,
                tp.product_name,
                tp.unit_nav,
                tp.cumulative_nav,
                tp.income_per_10k,
                CASE
                    WHEN tp.annualized_7d_or_growth IS NOT NULL
                         AND tp.annualized_7d_or_growth > 0
                        THEN tp.annualized_7d_or_growth
                    WHEN p.past_nav IS NOT NULL
                         AND COALESCE(tp.cumulative_nav, tp.unit_nav) IS NOT NULL
                         AND COALESCE(tp.cumulative_nav, tp.unit_nav) != 1.0
                         AND p.past_nav > 0
                         AND p.days_diff > 0
                        THEN ROUND(
                            (COALESCE(tp.cumulative_nav, tp.unit_nav) - p.past_nav) / p.past_nav
                            * (365.0 / p.days_diff) * 100,
                            4
                        )
                    ELSE NULL
                END AS effective_7d,
                tp.daily_growth_rate,
                tp.as_of_date,
                CASE
                    WHEN tp.annualized_7d_or_growth IS NOT NULL
                         AND tp.annualized_7d_or_growth > 0 THEN 'direct'
                    WHEN p.past_nav IS NOT NULL THEN 'calculated'
                    ELSE NULL
                END AS source
            FROM TargetProducts tp
            LEFT JOIN past_data p ON tp.product_code = p.product_code
        )
        SELECT m.product_code,
               m.product_name,
               m.unit_nav,
               m.cumulative_nav,
               m.income_per_10k,
               m.effective_7d,
               m.daily_growth_rate,
               m.as_of_date,
               m.source,
               rl.risk_level,
               rl.risk_label,
               lp.lockup_period_text,
               lp.lockup_period_days
        FROM merged m
        LEFT JOIN product_risk_levels rl ON m.product_code = rl.product_code
        LEFT JOIN product_lockup_periods lp ON m.product_code = lp.product_code
        WHERE m.effective_7d IS NOT NULL
          AND m.effective_7d > 0
          {risk_filter_clause}
        ORDER BY m.effective_7d DESC, m.as_of_date DESC
        LIMIT :lim
        """
    )

    rows = db.execute(sql, params).fetchall()

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
            lockup_period_text=r[11] if len(r) > 11 else None,
            lockup_period_days=r[12] if len(r) > 12 else None,
            lockup_period_source="manual" if len(r) > 11 and r[11] else None,
        )
        for r in rows
    ]

    if items:
        latest_date = max(i.as_of_date for i in items)
    else:
        latest_date = _find_reference_date(db) or "1970-01-01"

    return RankingResponse(as_of_date=latest_date, items=items)
