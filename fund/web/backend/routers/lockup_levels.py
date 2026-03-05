"""手动管理产品封闭期限的 API。

支持：
- PUT   /api/lockup-periods/{product_code}  —— 设置 / 更新封闭期限
- DELETE /api/lockup-periods/{product_code} —— 删除手动设置的封闭期限
- GET   /api/lockup-periods                 —— 列出所有已设置的封闭期限

优先级：手动设置 > 名称解析。任意同步脚本不得覆盖 source='manual' 的记录。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_db

router = APIRouter(prefix="/api/lockup-periods", tags=["lockup-periods"])

# 预设选项：展示文本 -> (展示文本, 天数)。天数为 -1 表示「未定义」用于筛选
LOCKUP_PRESETS = [
    ("日开", 1),
    ("7天", 7),
    ("14天", 14),
    ("30天", 30),
    ("90天", 90),
    ("180天", 180),
]


def _ensure_table(db: Session) -> None:
    """确保 product_lockup_periods 表存在。"""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS product_lockup_periods (
            product_code VARCHAR(64) PRIMARY KEY,
            lockup_period_text VARCHAR(32) NOT NULL,
            lockup_period_days INTEGER,
            source VARCHAR(20) NOT NULL DEFAULT 'manual',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.commit()


class LockupInput(BaseModel):
    lockup_period_text: str  # 如 "日开", "7天", "14天", "30天", "90天"
    lockup_period_days: Optional[int] = None  # 可选，用于筛选；为空时根据 text 推断


class LockupItem(BaseModel):
    product_code: str
    lockup_period_text: str
    lockup_period_days: Optional[int]
    source: str


def _text_to_days(text_val: str) -> Optional[int]:
    """将展示文本映射为天数，便于筛选。"""
    t = text_val.strip()
    for preset_text, days in LOCKUP_PRESETS:
        if t == preset_text:
            return days
    if "天" in t:
        try:
            return int("".join(c for c in t if c.isdigit()) or 0) or None
        except ValueError:
            pass
    if "月" in t:
        try:
            return int("".join(c for c in t if c.isdigit()) or 0) * 30 or None
        except ValueError:
            pass
    return None


# ---------- PUT ----------
@router.put("/{product_code}")
def set_lockup_period(
    product_code: str,
    body: LockupInput,
    db: Session = Depends(get_db),
):
    """设置产品的封闭期限。仅接受预设或合理格式。"""
    _ensure_table(db)

    text_val = body.lockup_period_text.strip()
    if not text_val:
        raise HTTPException(status_code=400, detail="封闭期限不能为空")

    days = body.lockup_period_days
    if days is None:
        days = _text_to_days(text_val)

    db.execute(
        text("""
            INSERT INTO product_lockup_periods
                (product_code, lockup_period_text, lockup_period_days, source, updated_at)
            VALUES (:code, :text, :days, 'manual', CURRENT_TIMESTAMP)
            ON CONFLICT(product_code) DO UPDATE SET
                lockup_period_text = :text,
                lockup_period_days = :days,
                source = 'manual',
                updated_at = CURRENT_TIMESTAMP
        """),
        {"code": product_code, "text": text_val, "days": days},
    )
    db.commit()

    return {"ok": True, "product_code": product_code, "lockup_period_text": text_val, "lockup_period_days": days}


# ---------- DELETE ----------
@router.delete("/{product_code}")
def delete_lockup_period(
    product_code: str,
    db: Session = Depends(get_db),
):
    result = db.execute(
        text("DELETE FROM product_lockup_periods WHERE product_code = :code"),
        {"code": product_code},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="该产品没有设置封闭期限")

    return {"ok": True, "product_code": product_code}


# ---------- GET list ----------
@router.get("", response_model=list[LockupItem])
def list_lockup_periods(
    db: Session = Depends(get_db),
):
    """列出所有已手动设置的封闭期限。"""
    _ensure_table(db)

    rows = db.execute(
        text(
            "SELECT product_code, lockup_period_text, lockup_period_days, source "
            "FROM product_lockup_periods ORDER BY product_code"
        )
    ).fetchall()

    return [
        LockupItem(
            product_code=r[0],
            lockup_period_text=r[1],
            lockup_period_days=r[2],
            source=r[3],
        )
        for r in rows
    ]
