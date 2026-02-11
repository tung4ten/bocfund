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
    as_of_date: date
    annualized_7d_source: Optional[str] = None  # "direct" | "calculated" | None
    risk_level: Optional[str] = None            # "R1" | "R2" | "R3" | "R4" | "R5" | None
    risk_label: Optional[str] = None            # "低风险" | "中低风险" | "中风险" | "中高风险" | None


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


class PortfolioResponse(BaseModel):
    products: List[ProductSnapshot]


class CompareResponse(BaseModel):
    series: List[ProductHistory]
