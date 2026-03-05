from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class ProductSnapshot(BaseModel):
    product_code: str
    product_name: str
    unit_nav: Optional[float] = None
    cumulative_nav: Optional[float] = None
    income_per_10k: Optional[float] = None
    annualized_7d: Optional[float] = None
    daily_growth_rate: Optional[float] = None
    day_nav_change: Optional[float] = None      # New: Absolute change in NAV (Unit or Cumulative)
    as_of_date: date
    period_days: Optional[int] = None
    annualized_7d_source: Optional[str] = None  # "direct" | "calculated" | None
    risk_level: Optional[str] = None            # "R1" | "R2" | "R3" | "R4" | "R5" | None
    risk_label: Optional[str] = None            # "低风险" | "中低风险" | "中风险" | "中高风险" | None
    lockup_period_text: Optional[str] = None    # "日开" | "7天" | ... 手动设置或名称解析
    lockup_period_days: Optional[int] = None    # 用于筛选：1,7,14,30,90 等
    lockup_period_source: Optional[str] = None  # "manual" 手动设置 | "name" 名称解析 | None 未定义


class RankingResponse(BaseModel):
    as_of_date: date
    items: List[ProductSnapshot]


class HistoryPoint(BaseModel):
    as_of_date: date
    annualized_7d: Optional[float] = None
    income_per_10k: Optional[float] = None
    cumulative_nav: Optional[float] = None
    daily_growth_rate: Optional[float] = None


class ProductHistory(BaseModel):
    product_code: str
    product_name: str
    history: List[HistoryPoint]
    risk_level: Optional[str] = None
    lockup_period_text: Optional[str] = None
    lockup_period_days: Optional[int] = None
    lockup_period_source: Optional[str] = None


class PortfolioResponse(BaseModel):
    products: List[ProductSnapshot]


class CompareResponse(BaseModel):
    series: List[ProductHistory]
