
import sqlite3
import datetime
from decimal import Decimal

DB_PATH = '/opt/bocfund/fund/data/boc_nav.sqlite3'

def debug_calc():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # 1. Get Holdings
    holdings = {}
    rows = conn.execute('SELECT product_code, SUM(shares) as s FROM portfolio_transactions GROUP BY product_code').fetchall()
    for r in rows:
        holdings[r['product_code']] = float(r['s'])
        
    print(f"Holdings loaded: {len(holdings)} products")
    
    # 2. Load NAV Data for last 20 days
    start_date = '2026-01-20'
    today = datetime.date.today()
    
    codes = list(holdings.keys())
    placeholders = ",".join([f"'{c}'" for c in codes])
    
    sql = f"""
    SELECT product_code, as_of_date, unit_nav, cumulative_nav 
    FROM boc_nav_records 
    WHERE product_code IN ({placeholders}) 
      AND as_of_date >= '{start_date}'
    ORDER BY as_of_date
    """
    
    nav_rows = conn.execute(sql).fetchall()
    nav_map = {}
    for r in nav_rows:
        c = r['product_code']
        d = r['as_of_date'] # string YYYY-MM-DD
        if c not in nav_map: nav_map[c] = {}
        nav_map[c][d] = {
            'unit': float(r['unit_nav']) if r['unit_nav'] else None,
            'cum': float(r['cumulative_nav']) if r['cumulative_nav'] else None
        }
        
    # 3. Simulate last few days
    check_dates = [
        datetime.date(2026, 2, 8),
        datetime.date(2026, 2, 9),
        datetime.date(2026, 2, 10),
        datetime.date(2026, 2, 11),
        datetime.date(2026, 2, 12)
    ]
    
    for d in check_dates:
        d_str = d.isoformat()
        print(f"\n--- Checking {d_str} ---")
        total_asset = 0.0
        total_income = 0.0
        
        for code, shares in holdings.items():
            if shares == 0: continue
            
            p_data = nav_map.get(code, {})
            today_nav = p_data.get(d_str)
            
            # Asset Calc
            effective_nav = today_nav
            source = "Today"
            if not effective_nav:
                for back in range(1, 16):
                    bd = (d - datetime.timedelta(days=back)).isoformat()
                    if bd in p_data:
                        effective_nav = p_data[bd]
                        source = f"Back-{back} ({bd})"
                        break
            
            val = 0.0
            if effective_nav:
                if effective_nav['unit'] is not None:
                    val = shares * effective_nav['unit']
                elif effective_nav['cum'] is not None:
                    val = shares * effective_nav['cum']
            total_asset += val
            
            # Income Calc (Simplified check)
            pnl = 0.0
            if today_nav:
                # Debug script fix: Access keys carefully or ensure they exist
                # 'today_nav' is a dict created earlier.
                if today_nav.get('inc') is not None:
                    pnl = shares * today_nav['inc'] / 10000.0
                elif today_nav.get('cum') is not None:
                    # Find prev
                    prev_cum = None
                    for back in range(1, 15):
                         bd = (d - datetime.timedelta(days=back)).isoformat()
                         if bd in p_data and p_data[bd]['cum'] is not None:
                             prev_cum = p_data[bd]['cum']
                             break
                    if prev_cum is not None:
                        pnl = shares * (today_nav['cum'] - prev_cum)
            
            total_income += pnl
            if pnl != 0:
                print(f"  Income [{code}]: {pnl:.2f} (Shares: {shares})")

        print(f"Total Asset: {total_asset:,.2f} | Total Daily Income: {total_income:,.2f}")

    # --- Verbose Trace for one Net Value Product ---
    print("\n--- Detailed Trace for 132039D (Net Value) ---")
    trace_code = "132039D"
    if trace_code in holdings:
        s = holdings[trace_code]
        p_data = nav_map.get(trace_code, {})
        # Sort dates
        dates = sorted(p_data.keys())
        # Filter last 10
        dates = dates[-10:]
        
        for d in dates:
            data = p_data[d]
            cum = data.get('cum')
            print(f"Date: {d}, CumNAV: {cum}")
            # Try to calc income manually
            # Find prev
            curr_date_obj = datetime.date.fromisoformat(d)
            prev_cum = None
            prev_date_str = ""
            for back in range(1, 15):
                 bd = (curr_date_obj - datetime.timedelta(days=back)).isoformat()
                 if bd in p_data and p_data[bd].get('cum') is not None:
                     prev_cum = p_data[bd]['cum']
                     prev_date_str = bd
                     break
            
            if prev_cum is not None and cum is not None:
                diff = cum - prev_cum
                inc = s * diff
                print(f"  -> Prev Date: {prev_date_str}, Prev Cum: {prev_cum}")
                print(f"  -> Diff: {diff:.6f}, Shares: {s}, Income: {inc:.2f}")
            else:
                print("  -> No prev data found or current data missing")

    conn.close()

if __name__ == "__main__":
    debug_calc()
