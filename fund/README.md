# 中国银行「当日代销理财产品净值」全量抓取器

本工具抓取并解析中国银行官网页面的“当日代销理财产品净值”全站分页数据，写入 SQLite 数据库，支持幂等 Upsert。

- 数据源：`https://www.bankofchina.com/sourcedb/srfd6_2024/index.html`
- 版权与免责声明：仅用于学习与技术研究，以上产品净值以产品管理人公布为准。

## 快速开始

1) 安装依赖（建议虚拟环境）

```bash
pip install -r fund/requirements.txt
```

2) 运行全量抓取（自动探测总页数）

```bash
python -m fund.boc_scraper.cli
```

3) 指定数据库路径或起止页

```bash
python -m fund.boc_scraper.cli --db-path fund/data/boc_nav.sqlite3 --from-page 1 --to-page 10
```

4) 仅测试抓取（不落库）

```bash
python -m fund.boc_scraper.cli --dry-run
```

5) 导出 Excel 透视表（按日期展开累计净值）

```bash
python -m fund.boc_scraper.export_excel
```

可选参数：

- 指定数据库：`--db-path your/path.sqlite3`
- 指定输出文件：`--output your/report.xlsx`（最终文件会自动追加 `_YYYYMMDD` 后缀）

## 环境变量

- `BOC_DB_PATH`：指定 SQLite 数据库文件路径（例如：`D:/data/boc_nav.sqlite3`）。若未设置，默认写入 `fund/data/boc_nav.sqlite3`。

## 数据库结构

表：`boc_nav_records`（主键：`product_code` + `as_of_date`）

- `product_code`：产品代码
- `as_of_date`：截止日期（日期）
- `product_name`：产品名称
- `unit_nav`：单位净值（Decimal）
- `cumulative_nav`：累计净值（Decimal）
- `income_per_10k`：每万份基金单位收益（Decimal）
- `annualized_7d_or_growth`：七日年收益率/净值增长率（Decimal）
- `daily_growth_rate`：日净值增长率（Decimal）
- `source_page_url`：来源页面 URL
- `created_at`/`updated_at`：入库/更新时间

## 注意事项

- 抓取逻辑包含简单的重试与请求间隔，避免对目标网站造成压力。
- 分页规则按官网常见模式处理：第 1 页 `index.html`，第 N 页 `index_N.html`。
- 如遇页面结构变化或列名调整，可在 `fund/boc_scraper/scraper.py` 中调整解析逻辑。

## 引用

- 中国银行官网当日代销理财产品净值：[`https://www.bankofchina.com/sourcedb/srfd6_2024/index.html`](https://www.bankofchina.com/sourcedb/srfd6_2024/index.html)


