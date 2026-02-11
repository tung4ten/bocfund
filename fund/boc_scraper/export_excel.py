from __future__ import annotations

import argparse
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from openpyxl import Workbook

DEFAULT_DB_PATH = "fund/data/boc_nav.sqlite3"
DEFAULT_OUTPUT_PATH = "fund/output/boc_nav_pivot.xlsx"


def append_date_suffix(path: str) -> str:
    """
    在文件名结尾追加 _YYYYMMDD 后缀（保留原扩展名）。
    """
    target = Path(path)
    date_suffix = datetime.now().strftime("%Y%m%d")
    if target.suffix:
        new_name = f"{target.stem}_{date_suffix}{target.suffix}"
    else:
        new_name = f"{target.name}_{date_suffix}"
    return str(target.with_name(new_name))


def load_records(db_path: str) -> Tuple[List[str], Dict[str, Dict[str, float]], Dict[str, str]]:
    """
    返回值：
    - sorted_dates: 排序后的日期列表（字符串，YYYY-MM-DD）
    - pivot: {product_code: {date: cumulative_nav}}
    - names: {product_code: product_name}
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT product_code, product_name, as_of_date, cumulative_nav
            FROM boc_nav_records
            ORDER BY product_code, as_of_date
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    dates_set = set()
    pivot: Dict[str, Dict[str, float]] = defaultdict(dict)
    names: Dict[str, str] = {}

    for product_code, product_name, as_of_date, cumulative_nav in rows:
        if as_of_date is None:
            continue
        date_str = str(as_of_date)
        dates_set.add(date_str)
        names[product_code] = product_name
        pivot[product_code][date_str] = float(cumulative_nav) if cumulative_nav is not None else None

    sorted_dates = sorted(dates_set, reverse=True)
    return sorted_dates, pivot, names


def export_to_excel(sorted_dates: List[str], pivot: Dict[str, Dict[str, float]], names: Dict[str, str], output_path: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "NAV Pivot"

    header = ["产品名称", "产品代码", *sorted_dates]
    ws.append(header)

    for product_code in sorted(pivot.keys(), key=lambda code: (names.get(code, ""), code)):
        row = [names.get(product_code, ""), product_code]
        navs = pivot[product_code]
        for date in sorted_dates:
            value = navs.get(date)
            row.append(value)
        ws.append(row)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m fund.boc_scraper.export_excel",
        description="将 boc_nav.sqlite3 中的数据透视成 Excel（按日期展开累计净值）",
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help="SQLite 数据库路径（默认：fund/data/boc_nav.sqlite3）",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help="输出 Excel 文件路径（默认：fund/output/boc_nav_pivot.xlsx）",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    dates, pivot, names = load_records(args.db_path)
    if not dates:
        print("[警告] 数据库中没有可用的数据记录。")
        return 1

    output_path = append_date_suffix(args.output)
    export_to_excel(dates, pivot, names, output_path)
    print(f"[完成] 已生成 Excel：{output_path}")
    print(f"[统计] 产品数量：{len(pivot)}, 日期列数：{len(dates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


