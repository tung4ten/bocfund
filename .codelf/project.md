## BOC Fund NAV Dashboard (中国银行理财净值看板)

> 抓取中国银行官网"当日代销理财产品净值"全站分页数据，存入 SQLite，并通过 Web 看板展示七日年化 Top 50 排行、个人持仓收益跟踪、产品趋势对比图表。

> **数据源**: https://www.bankofchina.com/sourcedb/srfd6_2024/index.html

> **项目状态**: 生产运行中。爬虫定时任务每日 16:00 自动执行，Web 看板已搭建完成。

> **团队**: 个人项目

> **技术栈**: Python 3.10+ / FastAPI / SQLAlchemy / SQLite / Vue 3 / Vite / TailwindCSS / ECharts


## Dependencies

### Python 后端 (fund/requirements.txt)
* requests (2.32.3): HTTP 请求库，用于爬虫抓取网页
* beautifulsoup4 (4.12.3): HTML 解析库，用于解析中行网页表格
* SQLAlchemy (2.0.34): ORM 框架，定义数据模型和 Upsert 操作
* openpyxl (3.1.5): Excel 读写库，用于导出透视表
* fastapi (>=0.115.0): Web API 框架
* uvicorn[standard] (>=0.30.0): ASGI 服务器
* pydantic (>=2.0): 数据验证和序列化

### 前端 (fund/web/frontend/package.json)
* vue (3.x): 前端 SPA 框架
* vue-router (4.x): 路由管理
* axios: HTTP 客户端，调用后端 API
* echarts + vue-echarts: 图表库，用于趋势折线图
* tailwindcss (v4): CSS 工具类框架
* vite: 前端构建工具
* typescript: 类型安全


## Development Environment

> **Python**: 3.10+ (系统 Python，无 venv)
> **Node.js**: 22.x + npm 10.x
> **Database**: SQLite 3 (文件: fund/data/boc_nav.sqlite3)
> **OS**: Linux (Ubuntu)

### 启动命令

**后端开发模式** (自动重载):
```bash
cd /opt/bocfound
python3 -m uvicorn fund.web.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端开发模式** (Vite dev server + API 代理):
```bash
cd /opt/bocfound/fund/web/frontend
npm run dev
```

**生产模式** (前端打包 + FastAPI 托管静态文件):
```bash
cd /opt/bocfound/fund/web/frontend && npm run build
cd /opt/bocfound && python3 -m uvicorn fund.web.backend.main:app --host 0.0.0.0 --port 8000
```

**爬虫手动执行**:
```bash
cd /opt/bocfound
python3 -m fund.boc_scraper.cli                    # 全量抓取（完成后自动同步风险等级）
python3 -m fund.boc_scraper.cli --skip-risk-sync   # 全量抓取，跳过风险等级同步
python3 -m fund.boc_scraper.cli --dry-run           # 测试模式
python3 -m fund.boc_scraper.export_excel            # 导出 Excel
```

**风险等级同步**:
```bash
cd /opt/bocfound
python3 -m fund.boc_scraper.sync_risk_levels        # 增量同步（仅补全新产品）
python3 -m fund.boc_scraper.sync_risk_levels --full  # 全量刷新 BOCWM 数据
```

**Docker 部署**:
```bash
cd /opt/bocfound/fund
docker-compose up --build
```


## Structure

> 核心项目代码在 fund/ 目录下。.venv/ 是 Windows 旧虚拟环境（不在 Linux 上使用），qoder-rules/ 是编码规范文档。

```
root (/opt/bocfound)
- .codelf/                          # 项目文档（本文件所在目录）
- .venv/                            # [不使用] Windows 旧虚拟环境，Linux 下使用系统 Python
- qoder-rules/                      # [参考] 编码规范文档集合
- logs/
    - task.log                      # 定时任务日志（爬虫+导出的每日运行记录）
- fund/                             # ★ 主项目目录
    - README.md                     # 项目说明文档
    - requirements.txt              # Python 依赖清单（爬虫 + Web 后端）
    - portfolio.json                # ★ 持仓产品代码配置文件（手动编辑，API 实时读取，无需重启服务）
    - Dockerfile                    # 多阶段构建（Node编译前端 + Python运行后端）
    - docker-compose.yml            # 一键部署编排
    - data/
        - boc_nav.sqlite3           # ★ SQLite 数据库，约 91K 条记录，7600+ 产品
                                    #   含 product_risk_levels 表（风险等级，来自 BOCWM API）
        - risk_levels.json          # BOCWM API 原始风险等级数据快照（2082 个中银理财产品）
    - output/
        - boc_nav_pivot_*.xlsx      # 每日自动生成的 Excel 透视表（按日期展开累计净值）
    - boc_scraper/                  # ★ 爬虫模块（定时任务核心）
        - __init__.py               # 包定义，exports: db, scraper
        - cli.py                    # ★ CLI 入口：探测总页数 → 全量抓取 → Upsert 入库 → 同步风险等级
                                    #   参数: --base-url, --db-path, --from-page, --to-page, --dry-run, --skip-risk-sync
        - sync_risk_levels.py       # ★ 风险等级同步脚本
                                    #   数据来源: 中银理财官网 API (bocwm.cn/webApi/cms/product/queryStaticProducts)
                                    #   仅存储官方数据，不做推断；未覆盖的代销产品显示为空
                                    #   爬虫 cli.py 完成后自动调用，也可独立运行
        - scraper.py                # ★ 核心爬虫逻辑
                                    #   BocScraper 类: 页面发现、HTTP 请求(重试+delay)、HTML表格解析
                                    #   解析 8 列: 产品代码/名称/单位净值/累计净值/万份收益/七日年化/日增长率/截止日期
                                    #   支持 iframe 回退解析
                                    #   ScrapeStats 数据类: 统计抓取结果
        - db.py                     # ★ 数据库层
                                    #   BocNavRecord ORM 模型（复合主键: product_code + as_of_date）
                                    #   字段: unit_nav, cumulative_nav, income_per_10k, annualized_7d_or_growth,
                                    #          daily_growth_rate, source_page_url, created_at, updated_at
                                    #   upsert_records(): SQLite ON CONFLICT DO UPDATE，批次大小 200
                                    #   get_engine(): 数据库连接工厂
        - export_excel.py           # Excel 导出工具
                                    #   load_records(): 从 SQLite 读取透视数据
                                    #   export_to_excel(): 输出行=产品、列=日期、值=累计净值的 pivot 表
                                    #   自动追加日期后缀到文件名
    - web/                          # ★ Web 看板模块（新增）
        - __init__.py
        - backend/                  # FastAPI 后端
            - __init__.py
            - main.py               # ★ FastAPI 入口: 挂载 API 路由 + CORS + 生产环境 SPA 静态文件托管
            - config.py             # ★ 配置中心: DB 路径/引擎、portfolio.json 读取、前端 dist 路径
                                    #   get_db(): FastAPI 依赖注入（每请求一个 Session）
                                    #   load_portfolio_codes(): 实时读取持仓代码列表
            - schemas.py            # Pydantic 响应模型: ProductSnapshot(含 risk_level, annualized_7d_source),
                                    #   RankingResponse, HistoryPoint, ProductHistory, PortfolioResponse, CompareResponse
            - routers/
                - __init__.py
                - ranking.py        # GET /api/ranking/top50?risk=R1,R2&limit=50
                                    #   合并直接提供 + 净值计算的七日年化，支持风险等级筛选
                                    #   选取数据充足的最近交易日（七日年化记录 >= 300）
                - portfolio.py      # GET /api/portfolio — 持仓产品最新指标
                                    # GET /api/portfolio/history?days=N — 持仓历史趋势数据
                - transactions.py   # ★ [新增] 持仓交易管理
                                    #   POST /api/transactions — 添加交易记录 (份额/日期)
                                    #   GET /api/transactions — 获取交易列表
                                    #   GET /api/transactions/income — 计算每日收益与总资产 (支持净值型/货币型混合计算)
                                    #   逻辑: 自动填充缺失净值(15天)，处理周末收益累积
                - products.py       # GET /api/products/{code}/history?days=N — 单产品历史
                                    # GET /api/products/compare?codes=A,B,C&days=N — 多产品对比
                - risk_levels.py    # ★ PUT /api/risk-levels/{product_code} — 手动设置风险等级 (R1-R5)
                                    #   DELETE /api/risk-levels/{product_code} — 删除风险等级
                                    #   GET /api/risk-levels?source=manual|bocwm — 列出所有风险等级
                                    #   手动设置的记录 source='manual'，与 BOCWM 数据共存
        - frontend/                 # Vue 3 + Vite + TailwindCSS + ECharts 前端
            - index.html            # SPA 入口
            - package.json          # 前端依赖
            - vite.config.ts        # Vite 配置（含开发模式 API 代理到 localhost:8000）
            - tsconfig*.json        # TypeScript 配置
            - dist/                 # 生产构建输出（npm run build 后生成，FastAPI 直接托管）
            - src/
                - main.ts           # Vue 应用入口，挂载 router
                - router.ts         # 路由定义: / (Dashboard) 和 /compare (趋势对比)
                - style.css         # 全局样式（TailwindCSS v4 导入）
                - App.vue           # 主布局: 顶部导航栏 + router-view
                - api/
                    - index.ts      # ★ Axios API 客户端: fetchTop50, fetchPortfolio,
                                    #   fetchPortfolioHistory, fetchProductHistory, fetchCompare,
                                    #   setRiskLevel, deleteRiskLevel
                                    #   类型定义: ProductSnapshot, HistoryPoint, ProductHistory 等
                - views/
                    - Dashboard.vue # ★ 首页看板: 持仓概览卡片 + Top 50 排行表格
                    - MyPositions.vue # ★ [新增] 我的持仓: 交易记录增删查改 + 每日收益/总资产双轴图表
                    - Compare.vue   # ★ 趋势对比: 产品选择(持仓/手动) + 时间范围 + ECharts折线图 + 数据表
                - components/
                    - PortfolioCards.vue  # 持仓卡片组: 显示七日年化/万份收益 + 迷你趋势 sparkline
                    - TopRanking.vue     # 排行表: 风险等级筛选下拉 + 搜索/勾选/对比，显示来源标签
                                         #   ★ 风险列可点击编辑：已有等级点击修改，无等级点击"+"添加
                    - TrendChart.vue     # ECharts 多产品七日年化折线图（支持缩放）
```


## Database Schema

表: `boc_nav_records` (复合主键: product_code + as_of_date)

| 字段 | 类型 | 说明 |
|---|---|---|
| product_code | VARCHAR(64) | 产品代码 (PK) |
| as_of_date | DATE | 截止日期 (PK) |
| product_name | VARCHAR(255) | 产品名称 |
| unit_nav | NUMERIC(18,6) | 单位净值 |
| cumulative_nav | NUMERIC(18,6) | 累计净值 |
| income_per_10k | NUMERIC(18,6) | 每万份基金单位收益（现金管理类产品关键指标） |
| annualized_7d_or_growth | NUMERIC(18,6) | 七日年收益率/净值增长率（现金管理类→七日年化；净值型→增长率） |
| daily_growth_rate | NUMERIC(18,6) | 日净值增长率（净值型产品关键指标） |
| source_page_url | VARCHAR(500) | 数据来源页面 URL |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

表: `product_risk_levels` (主键: product_code)

| 字段 | 类型 | 说明 |
|---|---|---|
| product_code | VARCHAR(64) | 产品代码 (PK) |
| risk_level | VARCHAR(10) | 风险等级 (R1-R5) |
| source | VARCHAR(20) | 来源 (bocwm/manual) |
| updated_at | DATETIME | 更新时间 |

表: `portfolio_transactions` (主键: id)

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 自增 ID |
| product_code | VARCHAR(64) | 产品代码 |
| date | TEXT | 交易日期 (YYYY-MM-DD) |
| shares | REAL | 份额 (支持小数) |
| amount | REAL | 金额 (参考值) |
| created_at | TIMESTAMP | 创建时间 |

> BOCWM 自动同步覆盖中银理财自有产品（2,082 个）；代销产品可通过前端排行榜页面手动设置风险等级（source='manual'）。

### 产品分类

| 类型 | 数量 | 关键指标 | 特征 |
|---|---|---|---|
| 现金管理类 | ~381 | income_per_10k + annualized_7d_or_growth | unit_nav/cumulative_nav 恒为 1.0 |
| 净值型 | ~6,767 | cumulative_nav + daily_growth_rate | annualized_7d_or_growth 为空 |
