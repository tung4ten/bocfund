from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from .db import BocNavRecord, create_tables, get_engine, upsert_records
from .scraper import BocScraper
from .sync_risk_levels import sync as sync_risk_levels


def _positive_int(value: str) -> int:
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"无效页码: {value}")
    return ivalue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m fund.boc_scraper.cli",
        description="抓取中国银行 当日代销理财产品净值 列表并写入数据库",
    )
    parser.add_argument(
        "--base-url",
        default="https://www.bankofchina.com/sourcedb/srfd6_2024/index.html",
        help="起始列表页 URL（默认：中行当日代销理财产品净值首页）",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="SQLite 数据库文件路径（默认：fund/data/boc_nav.sqlite3 或环境变量 BOC_DB_PATH）",
    )
    parser.add_argument(
        "--from-page",
        type=_positive_int,
        default=1,
        help="起始页（默认 1）",
    )
    parser.add_argument(
        "--to-page",
        type=_positive_int,
        default=None,
        help="结束页（默认自动探测总页数）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印统计信息，不写入数据库",
    )
    parser.add_argument(
        "--skip-risk-sync",
        action="store_true",
        help="跳过风险等级同步（默认：爬取完成后自动同步新产品的风险等级）",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    scraper = BocScraper(base_url=args.base_url)

    # 计算页码范围
    if args.to_page is None:
        total_pages = scraper.discover_total_pages()
        to_page = total_pages
    else:
        to_page = args.to_page

    if args.from_page > to_page:
        print(f"[错误] 起始页({args.from_page})不能大于结束页({to_page})", file=sys.stderr)
        return 2

    print(f"[信息] 抓取页码范围: {args.from_page} - {to_page}")
    print(f"[信息] 起始地址: {args.base_url}")

    # 抓取
    records, stats = scraper.scrape_range(args.from_page, to_page)

    print(
        f"[结果] 抓取完成: 页数={stats.total_pages}, 行数={stats.total_rows}, "
        f"耗时={stats.elapsed_seconds:.2f}s"
    )

    if args.dry_run:
        print("[信息] dry-run 模式，未写入数据库")
        return 0

    # 写入数据库（幂等 Upsert）
    engine = get_engine(args.db_path)
    create_tables(engine)
    with engine.begin() as conn:
        session = Session(bind=conn)
        affected = upsert_records(session, records)
    print(f"[结果] 已写入/更新记录: {affected}")

    # 自动同步新产品的风险等级
    if not args.skip_risk_sync:
        print("[信息] 同步风险等级...")
        try:
            risk_stats = sync_risk_levels(db_path=args.db_path)
            total_synced = risk_stats["bocwm_new"] + risk_stats["bocwm_updated"]
            if total_synced > 0:
                print(
                    f"[结果] 风险等级同步: 新增={risk_stats['bocwm_new']}, "
                    f"更新={risk_stats['bocwm_updated']}, "
                    f"保留手动={risk_stats['manual_kept']}, "
                    f"未覆盖={risk_stats['skipped']}"
                )
            else:
                print("[结果] 风险等级无需更新")
        except Exception as e:
            print(f"[警告] 风险等级同步失败（不影响数据入库）: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


















