from __future__ import annotations

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_db

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TransactionInput(BaseModel):
    product_code: str
    date: str  # YYYY-MM-DD
    shares: float  # Shares/Units. Positive for buy, negative for sell.
    amount: Optional[float] = 0.0  # Total value (CNY). Optional reference.


class TransactionItem(BaseModel):
    id: int
    product_code: str
    date: str
    shares: float
    amount: Optional[float]
    created_at: str


class DailyIncomePoint(BaseModel):
    date: str
    income: float
    total_asset: float


class IncomeResponse(BaseModel):
    series: List[DailyIncomePoint]
    total_income: float
    current_asset: float


# ---------------------------------------------------------------------------
# Database Init
# ---------------------------------------------------------------------------

def ensure_table(db: Session):
    db.execute(
        text("""
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT NOT NULL,
            date TEXT NOT NULL,
            shares REAL NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    )
    db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.on_event("startup")
def on_startup():
    # We can't easily get a session here without complex setup, 
    # so we rely on the first request or manual check.
    # Actually, let's just do it in the first request or lazily.
    pass


@router.get("", response_model=List[TransactionItem])
def list_transactions(db: Session = Depends(get_db)):
    ensure_table(db)
    rows = db.execute(
        text("SELECT id, product_code, date, shares, amount, created_at FROM portfolio_transactions ORDER BY date DESC, id DESC")
    ).fetchall()
    return [
        TransactionItem(
            id=r[0], product_code=r[1], date=r[2], shares=r[3], amount=r[4], created_at=str(r[5])
        )
        for r in rows
    ]


@router.post("", response_model=TransactionItem)
def add_transaction(item: TransactionInput, db: Session = Depends(get_db)):
    ensure_table(db)
    # Basic validation
    try:
        datetime.date.fromisoformat(item.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    cursor = db.execute(
        text("INSERT INTO portfolio_transactions (product_code, date, shares, amount) VALUES (:code, :date, :shares, :amount)"),
        {"code": item.product_code, "date": item.date, "shares": item.shares, "amount": item.amount or 0.0},
    )
    db.commit()
    new_id = cursor.lastrowid
    
    # Fetch back
    row = db.execute(
        text("SELECT id, product_code, date, shares, amount, created_at FROM portfolio_transactions WHERE id = :id"),
        {"id": new_id}
    ).fetchone()
    
    return TransactionItem(
        id=row[0], product_code=row[1], date=row[2], shares=row[3], amount=row[4], created_at=str(row[5])
    )


@router.delete("/{tid}")
def delete_transaction(tid: int, db: Session = Depends(get_db)):
    ensure_table(db)
    res = db.execute(text("DELETE FROM portfolio_transactions WHERE id = :id"), {"id": tid})
    db.commit()
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"ok": True}


@router.get("/income", response_model=IncomeResponse)
def get_daily_income(db: Session = Depends(get_db)):
    ensure_table(db)
    
    # 1. Get all transactions
    tx_rows = db.execute(
        text("SELECT product_code, date, shares, amount FROM portfolio_transactions ORDER BY date ASC")
    ).fetchall()
    
    if not tx_rows:
        return IncomeResponse(series=[], total_income=0, current_asset=0)

    # 2. Identify products and date range
    product_codes = set(r[0] for r in tx_rows)
    start_date = tx_rows[0][1]
    today_str = datetime.date.today().isoformat()
    
    # 3. Fetch NAV history for these products from start_date
    # We need a bit earlier for "yesterday" calculation and fill-forward lookback
    # Increased to 30 days to ensure we cover the 15-day lookback even for new transactions
    # FIX: Ensure we start looking for NAVs from BEFORE the first transaction date
    # to handle products bought on day 1.
    start_date_obj = datetime.date.fromisoformat(start_date)
    query_start = (start_date_obj - datetime.timedelta(days=30)).isoformat()
    
    # FIX: Ensure product_codes includes ALL products in transactions
    # The set 'product_codes' is already derived from 'tx_rows' above.
    
    placeholders = ",".join([f"'{c}'" for c in product_codes])
    nav_rows = db.execute(
        text(f"""
        SELECT product_code, as_of_date, unit_nav, cumulative_nav, income_per_10k 
        FROM boc_nav_records 
        WHERE product_code IN ({placeholders}) 
          AND as_of_date >= :start
        ORDER BY as_of_date ASC
        """),
        {"start": query_start}
    ).fetchall()
    
    # 4. Build NAV map
    # map[code][date] = { ... }
    nav_map = {}
    for r in nav_rows:
        code, date_str, unit, cum, inc = r
        if code not in nav_map:
            nav_map[code] = {}
        # Force date to string to ensure matching with d_str
        nav_map[code][str(date_str)] = {
            "unit": unit, 
            "cum": cum, 
            "inc": inc
        }

    # Debug: Check if we have data for specific product/date
    # print(f"DEBUG: NAV for AF246940G on 2026-02-09: {nav_map.get('AF246940G', {}).get('2026-02-09')}")

    # 5. Simulate timeline
    # We iterate from start_date to today
    current_date = start_date_obj
    end_date = datetime.date.today()
    
    holdings = {} # code -> shares
    series = []
    
    # Pre-process transactions into a map: date -> list of tx
    tx_by_date = {}
    for r in tx_rows:
        d = r[1]
        if d not in tx_by_date:
            tx_by_date[d] = []
        tx_by_date[d].append({"code": r[0], "shares": r[2]})

    total_income_accum = 0.0
    
    while current_date <= end_date:
        d_str = current_date.isoformat()
        
        # 1. Apply transactions happening TODAY (Start of Day or End of Day?)
        # Standard: Tx settled end of day. Income today is based on Holdings YESTERDAY.
        # But wait, if I buy on Friday, do I get weekend income?
        # Usually: Buy Fri -> Confirm Mon -> Earn from Mon/Tue.
        # Simplification: Buy Date D -> Holdings updated End of D -> Income starts D+1.
        
        # 2. Calculate Income for today based on START-OF-DAY Holdings (which is End-of-Prev-Day Holdings)
        daily_pnl = 0.0
        
        # Track MM reinvestment for this day to apply at end of loop
        mm_reinvest_shares = {} 

        # We must iterate ALL holdings, not just those with data today
        for code, shares in holdings.items():
            if shares == 0: continue
            
            p_data = nav_map.get(code, {})
            today_nav = p_data.get(d_str)
            
            # Debug log for a problematic date
            # if d_str == '2026-02-09':
            #     print(f"DEBUG {d_str}: {code} shares={shares} has_nav={today_nav is not None}")
            
            # --- Income Calculation ---
            # We calculate income if we have today's NAV
            if today_nav:
                # 1. Money Market (Income per 10k)
                # FIX: Only use MM logic if 'inc' is present AND non-zero.
                # Some Net Value products might have 'inc' column as 0.
                if today_nav.get('inc') is not None and float(today_nav['inc']) != 0:
                    # Daily income = Shares * Inc / 10000
                    inc_val = shares * float(today_nav['inc']) / 10000.0
                    daily_pnl += inc_val
                    
                    # Auto-reinvest for MM: Add income as new shares
                    unit_val = 1.0
                    if today_nav.get('unit') is not None:
                        unit_val = float(today_nav['unit'])
                    elif today_nav.get('cum') is not None:
                        unit_val = float(today_nav['cum'])
                        
                    if unit_val > 0:
                        added_shares = inc_val / unit_val
                        mm_reinvest_shares[code] = mm_reinvest_shares.get(code, 0.0) + added_shares
                
                # 2. Net Value Type (Diff in Cumulative NAV)
                elif today_nav.get('cum') is not None:
                    # Find previous NAV (strictly previous to today)
                    prev_nav_val = None
                    for lookback in range(1, 15):
                        p_d = (current_date - datetime.timedelta(days=lookback)).isoformat()
                        if p_d in p_data and p_data[p_d].get('cum') is not None:
                            prev_nav_val = float(p_data[p_d]['cum'])
                            break
                    
                    if prev_nav_val is not None:
                        # Income = Shares * (Today_Cum - Prev_Cum)
                        diff = float(today_nav['cum']) - prev_nav_val
                        daily_pnl += shares * diff
        
        # 3. Update Holdings (End of Day)
        # a) Apply Transactions
        if d_str in tx_by_date:
            for tx in tx_by_date[d_str]:
                c = tx["code"]
                s = tx["shares"]
                holdings[c] = holdings.get(c, 0.0) + s
        
        # b) Apply MM Reinvestment
        for c, s in mm_reinvest_shares.items():
            holdings[c] = holdings.get(c, 0.0) + s

        # 4. Recalculate Asset Value with Updated Holdings (End of Day View)
        total_asset_today = 0.0
        for code, shares in holdings.items():
            if shares == 0: continue
            
            p_data = nav_map.get(code, {})
            # Effective NAV lookup (Fill Forward)
            effective_nav = p_data.get(d_str)
            if not effective_nav:
                for back in range(1, 15):
                    bd = (current_date - datetime.timedelta(days=back)).isoformat()
                    if bd in p_data:
                        effective_nav = p_data[bd]
                        break
            
            if effective_nav:
                if effective_nav['unit'] is not None:
                    total_asset_today += shares * float(effective_nav['unit'])
                elif effective_nav['cum'] is not None:
                    total_asset_today += shares * float(effective_nav['cum'])

        # 5. Record Data Point
        if total_asset_today > 0:
             series.append(DailyIncomePoint(date=d_str, income=daily_pnl, total_asset=total_asset_today))
             total_income_accum += daily_pnl
            
        current_date += datetime.timedelta(days=1)

    return IncomeResponse(
        series=series,
        total_income=total_income_accum,
        current_asset=series[-1].total_asset if series else 0.0
    )
