"""手动管理产品风险等级的 API。

支持：
- PUT  /api/risk-levels/{product_code}  —— 设置 / 更新风险等级
- DELETE /api/risk-levels/{product_code} —— 删除手动设置的风险等级
- GET  /api/risk-levels                 —— 列出所有已设置的风险等级
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_db

router = APIRouter(prefix="/api/risk-levels", tags=["risk-levels"])

VALID_RISK_LEVELS = {"R1", "R2", "R3", "R4", "R5"}

RISK_LABEL_MAP = {
    "R1": "低风险",
    "R2": "中低风险",
    "R3": "中风险",
    "R4": "中高风险",
    "R5": "高风险",
}


class RiskLevelInput(BaseModel):
    risk_level: str  # R1 ~ R5


class RiskLevelItem(BaseModel):
    product_code: str
    risk_level: str
    risk_label: Optional[str] = None
    source: str


# ---------- PUT ----------
@router.put("/{product_code}")
def set_risk_level(
    product_code: str,
    body: RiskLevelInput,
    db: Session = Depends(get_db),
):
    level = body.risk_level.strip().upper()
    if level not in VALID_RISK_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的风险等级: {level}，有效值: {', '.join(sorted(VALID_RISK_LEVELS))}",
        )

    label = RISK_LABEL_MAP.get(level, "")

    db.execute(
        text("""
            INSERT INTO product_risk_levels
                (product_code, risk_level, risk_label, source, updated_at)
            VALUES (:code, :level, :label, 'manual', CURRENT_TIMESTAMP)
            ON CONFLICT(product_code) DO UPDATE SET
                risk_level = :level,
                risk_label = :label,
                source     = 'manual',
                updated_at = CURRENT_TIMESTAMP
        """),
        {"code": product_code, "level": level, "label": label},
    )
    db.commit()

    return {"ok": True, "product_code": product_code, "risk_level": level, "risk_label": label}


# ---------- DELETE ----------
@router.delete("/{product_code}")
def delete_risk_level(
    product_code: str,
    db: Session = Depends(get_db),
):
    result = db.execute(
        text("DELETE FROM product_risk_levels WHERE product_code = :code"),
        {"code": product_code},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="该产品没有设置风险等级")

    return {"ok": True, "product_code": product_code}


# ---------- GET list ----------
@router.get("", response_model=list[RiskLevelItem])
def list_risk_levels(
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """列出所有已设置的风险等级。可选按 source 筛选 (manual / bocwm)。"""
    if source:
        rows = db.execute(
            text(
                "SELECT product_code, risk_level, risk_label, source "
                "FROM product_risk_levels WHERE source = :src ORDER BY product_code"
            ),
            {"src": source},
        ).fetchall()
    else:
        rows = db.execute(
            text(
                "SELECT product_code, risk_level, risk_label, source "
                "FROM product_risk_levels ORDER BY product_code"
            )
        ).fetchall()

    return [
        RiskLevelItem(
            product_code=r[0], risk_level=r[1], risk_label=r[2], source=r[3]
        )
        for r in rows
    ]
