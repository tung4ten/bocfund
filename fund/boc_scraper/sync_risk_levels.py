"""同步产品风险等级。

数据来源：中银理财官网 API (bocwm.cn)，仅存储官方提供的风险等级，不做推断。
未覆盖的产品（主要是代销产品）可通过前端手动设置 (source='manual')。

覆盖策略：
- BOCWM 有值 → 写入/覆盖（无论原来是 bocwm 还是 manual）
- BOCWM 无值 → 保留原有数据（包括 manual 手动设置的值）

使用方式：
    python -m fund.boc_scraper.sync_risk_levels           # 仅补全新产品
    python -m fund.boc_scraper.sync_risk_levels --full     # 全量刷新（BOCWM 有值的覆盖，无值的保留）
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from typing import Optional

import requests
from sqlalchemy import text

from .db import get_engine

BOCWM_API_URL = "https://www.bocwm.cn/webApi/cms/product/queryStaticProducts"
BOCWM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bocwm.cn/html/1//151/183/index.html",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
}


def fetch_bocwm_risk_levels() -> dict[str, tuple[str, str]]:
    """从中银理财官网 API 拉取全部产品的风险等级。

    Returns:
        dict: {product_code: (risk_level, risk_label)}
    """
    result: dict[str, tuple[str, str]] = {}
    page = 1
    page_size = 200

    while True:
        try:
            resp = requests.post(
                BOCWM_API_URL,
                json={"pageNo": page, "pageSize": page_size},
                headers=BOCWM_HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [警告] BOCWM API 请求失败 (page={page}): {e}", file=sys.stderr)
            break

        rows = data.get("data", {}).get("rows", [])
        total = data.get("data", {}).get("total", 0)

        for row in rows:
            code = row.get("productCode")
            rl_raw = row.get("riskLevel", "")
            if code and rl_raw:
                m = re.match(r"(R\d)(.*)", rl_raw)
                if m:
                    result[code] = (m.group(1), m.group(2) or m.group(1))

        print(f"  BOCWM page {page}: +{len(rows)} (累计 {len(result)}/{total})")

        if len(result) >= total or len(rows) == 0:
            break
        page += 1
        time.sleep(0.3)

    return result


def sync(db_path: Optional[str] = None, full: bool = False) -> dict[str, int]:
    """同步产品风险等级到数据库。

    覆盖策略：
    - BOCWM 有值 → INSERT OR REPLACE（覆盖包括 manual 在内的所有旧值）
    - BOCWM 无值 → 不动（保留 manual 手动设置的值）

    Args:
        db_path: 数据库路径，None 则使用默认
        full: True 则全量刷新，False 仅补全新产品

    Returns:
        dict: {"bocwm_updated": N, "bocwm_new": N, "manual_kept": N, "skipped": N}
    """
    engine = get_engine(db_path)
    stats = {"bocwm_updated": 0, "bocwm_new": 0, "manual_kept": 0, "skipped": 0}

    with engine.connect() as conn:
        # 确保表存在
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_risk_levels (
                product_code VARCHAR(64) PRIMARY KEY,
                risk_level VARCHAR(20) NOT NULL,
                risk_label VARCHAR(20),
                source VARCHAR(20) NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()

        # 拉取 BOCWM 全量数据
        print("  拉取 BOCWM 风险等级数据...")
        bocwm_data = fetch_bocwm_risk_levels()

        if not bocwm_data:
            print("  [警告] 未获取到任何 BOCWM 数据")
            return stats

        # 读取当前数据库中的全部记录（用于统计和增量判断）
        r = conn.execute(text(
            "SELECT product_code, risk_level, source FROM product_risk_levels"
        ))
        existing = {row[0]: (row[1], row[2]) for row in r}

        if full:
            # 全量模式：BOCWM 有值的全部写入（覆盖 manual），BOCWM 无值的保留
            for code, (level, label) in bocwm_data.items():
                old = existing.get(code)
                if old and old[1] == "bocwm" and old[0] == level:
                    continue  # 相同值不需要更新
                conn.execute(text("""
                    INSERT INTO product_risk_levels
                        (product_code, risk_level, risk_label, source, updated_at)
                    VALUES (:code, :level, :label, 'bocwm', CURRENT_TIMESTAMP)
                    ON CONFLICT(product_code) DO UPDATE SET
                        risk_level = :level,
                        risk_label = :label,
                        source     = 'bocwm',
                        updated_at = CURRENT_TIMESTAMP
                """), {"code": code, "level": level, "label": label})
                if old:
                    stats["bocwm_updated"] += 1
                else:
                    stats["bocwm_new"] += 1
            conn.commit()

            # 统计保留的 manual 记录（BOCWM 未覆盖到的）
            stats["manual_kept"] = sum(
                1 for code, (_, src) in existing.items()
                if src == "manual" and code not in bocwm_data
            )
            print(
                f"  全量同步: 新增={stats['bocwm_new']}, "
                f"覆盖更新={stats['bocwm_updated']}, "
                f"保留手动={stats['manual_kept']}"
            )
        else:
            # 增量模式：仅写入数据库中还没有的产品（不覆盖已有记录）
            new_count = 0
            for code, (level, label) in bocwm_data.items():
                if code not in existing:
                    conn.execute(text("""
                        INSERT INTO product_risk_levels
                            (product_code, risk_level, risk_label, source, updated_at)
                        VALUES (:code, :level, :label, 'bocwm', CURRENT_TIMESTAMP)
                    """), {"code": code, "level": level, "label": label})
                    new_count += 1
            conn.commit()
            stats["bocwm_new"] = new_count
            print(f"  增量同步: 新增={new_count}")

        # 统计覆盖情况
        r = conn.execute(text("SELECT COUNT(*) FROM product_risk_levels"))
        total_risk = r.scalar()
        r = conn.execute(text("SELECT COUNT(*) FROM product_risk_levels WHERE source = 'manual'"))
        manual_count = r.scalar()
        r = conn.execute(text("SELECT COUNT(DISTINCT product_code) FROM boc_nav_records"))
        total_products = r.scalar()
        stats["skipped"] = total_products - total_risk
        print(
            f"  覆盖率: {total_risk}/{total_products} ({100*total_risk/total_products:.1f}%) "
            f"其中手动={manual_count}"
        )

    return stats


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m fund.boc_scraper.sync_risk_levels",
        description="从中银理财官网同步产品风险等级",
    )
    parser.add_argument(
        "--db-path", default=None, help="数据库路径（默认同爬虫）"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="全量刷新（默认仅补全新产品）"
    )
    args = parser.parse_args(argv)

    print("[开始] 同步产品风险等级...")
    stats = sync(db_path=args.db_path, full=args.full)
    print(f"[完成] 新增={stats['bocwm']}, 未覆盖={stats['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
