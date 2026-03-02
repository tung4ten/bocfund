## 2026-02-27 06:30:00

### 1. 高级排名功能

**Change Type**: feature

> **Purpose**: 新增高级排名功能，允许用户根据不同的时间周期（例如30天、90天、一年）计算年化收益率，并对理财产品进行排名。
> **Detailed Description**: 新增了 `advanced_ranking.py` 路由模块，提供 `/api/ranking/advanced` API 端点。该端点接受 `time_period_days` 参数，通过查询历史净值数据计算指定周期内的年化收益率。前端新增了 `AdvancedRanking.vue` 页面，提供输入框让用户指定时间周期，并以表格形式展示排名结果。
> **Reason for Change**: 用户希望能够筛选出在特定时间段内表现优异的理财产品，而不仅仅是基于7日年化收益率。
> **Impact Scope**: 新增后端路由和前端页面，对现有功能无影响。
> **API Changes**: 新增 `GET /api/ranking/advanced`

   ```
   fund/
   - web/backend/
     - main.py                               // refact: 注册 advanced_ranking router
     - routers/advanced_ranking.py       // add: 高级排名 API
   - web/frontend/src/
     - api/index.ts                      // refact: 新增 fetchAdvancedRanking()
     - views/AdvancedRanking.vue         // add: 高级排名页面
     - router.ts                         // refact: 添加 /advanced-ranking 路由
     - App.vue                           // refact: 在导航栏添加入口
   ```

---

## 2026-02-10 06:30:00

### 3. 手动管理风险等级（代销产品支持）

**Change Type**: feature

> **Purpose**: 允许用户在前端直接手动为任意产品设置风险等级，解决代销产品无法自动获取风险等级的问题
> **Detailed Description**: 新增 `risk_levels.py` 路由模块，提供 PUT/DELETE/GET 三个 RESTful API 端点管理风险等级。手动设置的记录在数据库 `product_risk_levels` 表中标记 `source='manual'`，与 BOCWM 自动同步的 `source='bocwm'` 数据共存。前端 TopRanking 风险列改造为可编辑：已有等级的产品点击标签弹出下拉修改，无等级的产品显示 `+` 按钮点击添加。支持 R1-R5 五个等级和清除操作。修改即时生效无需刷新页面。
> **Reason for Change**: 中银理财官网 API 仅覆盖自有产品（~2,082 个），代销产品（招银/交银/信银/平安等 ~5,500 个）无法自动获取风险等级。中国理财网 (chinawealth.com.cn) API 有严格反爬机制（验证码+频率限制），各代销机构官网也无统一公开接口。
> **Impact Scope**: 新增后端路由 + 前端编辑交互，数据库表结构无变化（复用已有 product_risk_levels 表）
> **API Changes**: 新增 `PUT /api/risk-levels/{code}`, `DELETE /api/risk-levels/{code}`, `GET /api/risk-levels`
> **Security Notes**: 无认证保护，仅适用于内部/个人使用场景

   ```
   fund/
   - web/backend/
     - main.py                       // refact: 注册 risk_levels router
     - routers/risk_levels.py        // add: 风险等级 CRUD API（PUT/DELETE/GET）
   - web/frontend/src/
     - api/index.ts                  // refact: 新增 setRiskLevel(), deleteRiskLevel()
     - components/TopRanking.vue     // refact: 风险列可编辑（点击标签/+ → 下拉选择 → 即时保存）
   ```

---

## 2026-02-10 01:30:00

### 1. 排行榜七日年化计算增强：净值型产品纳入排行

**Change Type**: improvement

> **Purpose**: 将排行榜从仅展示现金管理类产品（直接提供七日年化）扩展为全部产品类型
> **Detailed Description**: 对净值型产品，通过 `(最新累计净值 - 约7天前累计净值) / 约7天前累计净值 * (365/实际天数) * 100` 计算七日年化收益率。使用 SQL CTE + ROW_NUMBER 窗口函数在 4~10 天范围内选取最接近 7 天的历史净值。同时修复了排行日期选取逻辑：从盲取 MAX(as_of_date) 改为取最近一个数据充足的交易日（七日年化记录数 >= 300），避免假期/周末数据不全导致排行不准确。
> **Reason for Change**: 原排行仅覆盖 ~365 个现金管理类产品，6700+ 净值型产品被完全忽略
> **Impact Scope**: ranking.py API、schemas.py（新增 annualized_7d_source 字段）、前端 TopRanking.vue
> **API Changes**: ProductSnapshot 新增 `annualized_7d_source` 字段 ("direct" / "calculated")
> **Performance Impact**: 排行查询从简单 ORDER BY 变为 CTE + JOIN，但仍在毫秒级

   ```
   fund/
   - web/backend/
     - routers/ranking.py          // refact: CTE 合并直接值+计算值，数据充足日期选取
     - schemas.py                  // refact: ProductSnapshot 新增 annualized_7d_source
   - web/frontend/src/
     - api/index.ts                // refact: ProductSnapshot 类型新增 annualized_7d_source
     - components/TopRanking.vue   // refact: 显示来源标签（直接/计算）
   ```

### 2. 产品风险等级同步（BOCWM API）

**Change Type**: feature

> **Purpose**: 从中银理财官网 API 获取产品风险等级，用于排行榜筛选
> **Detailed Description**: 新增 `sync_risk_levels.py` 脚本，调用 `bocwm.cn/webApi/cms/product/queryStaticProducts` POST 接口分页拉取全部中银理财产品（2,082 个）的风险等级（R1-R4）。仅存储官方数据，不做推断，代销产品风险等级显示为空。脚本集成到爬虫 CLI 中，每次抓取完成后自动同步新产品。新建 `product_risk_levels` 表存储数据。排行 API 新增 `?risk=R1,R2` 筛选参数，前端新增风险等级彩色标签和下拉筛选器。
> **Reason for Change**: 用户需要按风险等级筛选排行，不同风险类型产品的收益率不具可比性
> **Impact Scope**: 新增脚本 + DB 表，修改 ranking API、schemas、CLI、前端 TopRanking
> **API Changes**: ProductSnapshot 新增 `risk_level`, `risk_label` 字段；ranking API 新增 `?risk` 查询参数
> **Configuration Changes**: 数据库新增 `product_risk_levels` 表
> **Performance Impact**: 风险等级同步需调用外部 API（~35 秒拉取 11 页），爬虫运行时间增加约 40 秒

   ```
   fund/
   - boc_scraper/
     - sync_risk_levels.py         // add: 风险等级同步脚本（BOCWM API）
     - cli.py                      // refact: 爬取后自动同步风险等级，新增 --skip-risk-sync 参数
   - data/
     - risk_levels.json            // add: BOCWM API 原始数据快照
   - web/backend/
     - routers/ranking.py          // refact: JOIN risk_levels 表，支持 ?risk 筛选
     - schemas.py                  // refact: ProductSnapshot 新增 risk_level, risk_label
   - web/frontend/src/
     - api/index.ts                // refact: 类型新增 risk_level, risk_label；fetchTop50 支持 risk 参数
     - components/TopRanking.vue   // refact: 风险等级彩色标签 + 下拉筛选器
   ```

---

## 2026-02-09 06:30:00

### 1. Web 看板搭建 (FastAPI + Vue 3 全栈)

**Change Type**: feature

> **Purpose**: 为理财净值数据提供可视化 Web 看板，替代纯 Excel 导出
> **Detailed Description**: 基于现有 SQLite 数据库，搭建前后端分离的 Web 应用。后端 FastAPI 提供 RESTful API（排行榜/持仓/对比），前端 Vue 3 + ECharts 实现数据看板（Top 50 排行、持仓卡片、趋势折线图）。
> **Reason for Change**: 之前仅有 Excel 导出功能，且只导出 cumulative_nav（对现金管理类产品无意义），无法直观查看七日年化收益率排行和趋势
> **Impact Scope**: 不影响现有爬虫模块和 Excel 导出，新增独立的 web/ 目录
> **API Changes**: 新增 5 个 API 端点 (/api/ranking/top50, /api/portfolio, /api/portfolio/history, /api/products/{code}/history, /api/products/compare)
> **Configuration Changes**: 新增 portfolio.json（持仓配置）、更新 requirements.txt（追加 fastapi/uvicorn/pydantic）
> **Performance Impact**: Web 服务与爬虫共享 SQLite 文件，读操作不影响写入性能

   ```
   fund/
   - portfolio.json                // add: 持仓产品代码配置文件
   - requirements.txt              // refact: 追加 fastapi, uvicorn, pydantic 依赖
   - Dockerfile                    // add: 多阶段构建（Node + Python）
   - docker-compose.yml            // add: 一键部署编排
   - web/                          // add: Web 看板模块
     - __init__.py                 // add: 包定义
     - backend/                    // add: FastAPI 后端
       - __init__.py
       - main.py                   // add: 应用入口，路由挂载 + SPA 静态托管
       - config.py                 // add: DB 连接、配置读取
       - schemas.py                // add: Pydantic 响应模型
       - routers/
         - __init__.py
         - ranking.py              // add: 排行榜 API
         - portfolio.py            // add: 持仓 API
         - products.py             // add: 产品查询/对比 API
     - frontend/                   // add: Vue 3 + Vite + TailwindCSS + ECharts
       - src/
         - App.vue                 // add: 主布局
         - router.ts               // add: 路由配置
         - api/index.ts            // add: API 客户端
         - views/Dashboard.vue     // add: 首页看板
         - views/Compare.vue       // add: 趋势对比页
         - components/PortfolioCards.vue  // add: 持仓卡片组
         - components/TopRanking.vue     // add: Top 50 排行表
         - components/TrendChart.vue     // add: 趋势折线图
   ```

---

## 2025-11-17 (项目初始版本)

### 1. 中国银行理财净值爬虫

**Change Type**: feature

> **Purpose**: 自动抓取中国银行官网"当日代销理财产品净值"全量数据
> **Detailed Description**: 实现 BocScraper 爬虫类，支持分页探测、HTML 表格解析、重试机制。数据通过 SQLAlchemy 写入 SQLite（upsert 幂等写入）。CLI 支持指定页码范围、dry-run 模式。
> **Reason for Change**: 需要定期获取理财产品净值数据用于分析
> **Impact Scope**: 独立模块
> **API Changes**: 无（CLI 工具）
> **Configuration Changes**: 环境变量 BOC_DB_PATH 可指定数据库路径
> **Performance Impact**: 全量抓取约 160 页，耗时 ~70 秒

   ```
   fund/
   - README.md                    // add: 项目说明
   - requirements.txt             // add: 依赖清单
   - boc_scraper/                 // add: 爬虫核心模块
     - __init__.py
     - cli.py                     // add: CLI 入口
     - scraper.py                 // add: 爬虫逻辑
     - db.py                      // add: 数据库层
     - export_excel.py            // add: Excel 导出
   - data/
     - boc_nav.sqlite3            // add: SQLite 数据库
   ```

### 2. Excel 透视表导出

**Change Type**: feature

> **Purpose**: 将数据库中的累计净值数据导出为按日期展开的 Excel 透视表
> **Detailed Description**: 从 SQLite 读取全量数据，生成行=产品、列=日期、值=累计净值的 pivot 表，每日自动追加日期后缀到文件名。
> **Reason for Change**: 便于在 Excel 中查看和分析产品净值变化
> **Impact Scope**: 独立功能，不影响爬虫
> **Configuration Changes**: 可通过 --output 参数指定输出路径
> **Performance Impact**: 数据量大时（7000+产品 x 1000+日期列）Excel 文件较大

   ```
   fund/
   - boc_scraper/
     - export_excel.py            // add: Excel 导出工具
   - output/
     - boc_nav_pivot_*.xlsx       // add: 每日生成的 Excel 文件
   ```
