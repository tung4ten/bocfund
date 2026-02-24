## Development Guidelines

### Framework and Language

**Framework Considerations:**
- **Python 后端 (FastAPI + SQLAlchemy)**:
  - 使用 SQLAlchemy 2.0 的新式 `mapped_column` 语法定义 ORM 模型
  - FastAPI 依赖注入模式管理 DB Session（`get_db()` yield pattern）
  - SQLite 连接需设置 `check_same_thread=False` 以支持多线程
  - Pydantic v2 用于 API 响应序列化
- **Vue 3 前端 (Composition API + TypeScript)**:
  - 全部使用 `<script setup lang="ts">` 语法
  - TailwindCSS v4 通过 `@tailwindcss/vite` 插件集成（非 PostCSS 配置方式）
  - ECharts 通过 `vue-echarts` 包装组件使用，需手动 `use()` 注册所需图表/组件
- **Importance Notes for Framework**:
  - SQLite 不支持真正的并发写入，爬虫和 Web 服务共享同一数据库文件时需注意
  - 前端生产构建输出到 `fund/web/frontend/dist/`，由 FastAPI 在 `main.py` 中直接 mount 托管
  - Vite 开发模式通过 `vite.config.ts` 中的 proxy 配置将 `/api` 请求代理到后端 8000 端口

**Language Best Practices:**
- Python: 使用 `from __future__ import annotations` 启用延迟类型注解
- Python: `Decimal` 类型处理净值数据精度，`_safe_decimal()` 处理各种空值/异常格式
- TypeScript: API 响应类型在 `src/api/index.ts` 中统一定义，确保前后端类型一致
- 中文：项目面向中文用户，所有 UI 文本、日志、CLI 提示均使用中文

### Code Abstraction and Reusability

**Modular Design Principles:**
- 爬虫模块 (`boc_scraper/`) 与 Web 模块 (`web/`) 完全解耦，仅通过 SQLite 数据库共享数据
- `portfolio.json` 作为配置文件独立于代码，支持热更新（API 每次请求重新读取）
- 前端 API 层 (`src/api/index.ts`) 封装所有后端调用，组件不直接使用 axios

**Reusable Component Library:**
```
fund/
- boc_scraper/
    - scraper.py          # BocScraper 类可复用于类似的分页表格抓取场景
    - db.py               # upsert_records() 通用的 SQLite 批量 upsert 实现
    - sync_risk_levels.py # BOCWM API 风险等级同步，可独立运行或被 cli.py 自动调用
- web/
    - backend/
        - config.py       # get_db() 依赖注入、load_portfolio_codes() 配置读取
        - schemas.py      # Pydantic 模型可复用于其他 API 扩展
    - frontend/
        - src/api/index.ts        # 统一的 API 客户端和类型定义
        - src/components/
            - TrendChart.vue      # 通用多产品趋势折线图，接收 ProductHistory[] props
            - TopRanking.vue      # 通用排行表格，支持搜索/勾选/事件发射
            - PortfolioCards.vue   # 持仓卡片组，含 sparkline 迷你图
```

### Coding Standards and Tools

**Code Formatting Tools:**
- TypeScript 使用 Vue TSC 进行类型检查 (`npx vue-tsc --noEmit`)
- Python 无强制 linter（建议后续加入 ruff/black）
- CSS 使用 TailwindCSS 工具类，无需额外 CSS linter

**Naming and Structure Conventions:**
- Python 后端: snake_case（文件名、变量名、函数名）
- Vue 前端: PascalCase（组件文件名如 `TopRanking.vue`），camelCase（变量/函数）
- API URL: kebab-case + RESTful 风格（`/api/ranking/top50`、`/api/portfolio/history`）
- 数据库字段: snake_case（`product_code`、`as_of_date`、`annualized_7d_or_growth`）

### Frontend-Backend Collaboration Standards

**API Design and Documentation:**
- RESTful 设计: GET 读取，PUT 更新/创建，DELETE 删除
- FastAPI 自动生成 OpenAPI 文档: `http://localhost:8000/docs`
- 统一响应格式:
  - 排行: `{ as_of_date, items: ProductSnapshot[] }`
  - 持仓: `{ products: ProductSnapshot[] }`
  - 历史/对比: `{ series: ProductHistory[] }`
- Query 参数: `days`(天数范围), `limit`(条数), `codes`(逗号分隔产品代码), `risk`(风险等级筛选如 `R1,R2,UNDEFINED`，支持多选), `source`(风险等级来源筛选)
- 风险等级 API: `PUT /api/risk-levels/{code}` (body: `{risk_level: "R1"}`), `DELETE /api/risk-levels/{code}`, `GET /api/risk-levels?source=manual`

**Data Flow:**
- 前端无状态管理库（Pinia），每个页面/组件独立请求数据（`onMounted` 时 fetch）
- 路由参数传递对比产品代码：`/compare?codes=A,B,C`
- 组件间通信通过 `emit` 事件（如 TopRanking 勾选产品 → Dashboard 跳转对比页）

### Performance and Security

**Performance Optimization Focus:**
- 爬虫请求间隔 0.4s（`request_delay_seconds`），避免对目标网站造成压力
- SQLite upsert 批次大小 200 条，平衡内存与写入效率
- 前端路由懒加载（`() => import('./views/Dashboard.vue')`）
- ECharts 大数据量时启用 `dataZoom` 组件（>60 天数据时自动启用滑动条）
- 前端生产构建约 710KB（gzip 后约 250KB）

**Security Measures:**
- 仅供内部/个人使用，无用户认证系统
- CORS 配置为 `allow_origins=["*"]`（本地使用，部署到公网时应限制）
- portfolio.json 为本地文件，不暴露写入 API
- 数据库：Web 端可通过 `/api/risk-levels` 写入 `product_risk_levels` 表（手动风险等级），其余数据仅爬虫写入
- 风险等级 API 无认证保护，部署到公网时应考虑添加

### Key Data Notes

**两类产品的区分很重要:**
- **现金管理类** (~381个): `unit_nav`/`cumulative_nav` 恒为 1.0，关注 `annualized_7d_or_growth`(七日年化) 和 `income_per_10k`(万份收益)
- **净值型** (~6,767个): `annualized_7d_or_growth` 为空，关注 `cumulative_nav`(累计净值) 和 `daily_growth_rate`(日增长率)

**排行榜七日年化数据来源:**
- `source=direct`: 现金管理类产品，直接读取 `annualized_7d_or_growth` 字段
- `source=calculated`: 净值型产品，通过 `(最新净值 - 7天前净值) / 7天前净值 × (365/天数) × 100` 计算
- 排行计算方式: 每个产品取其最新可用日期数据参与排行，不要求全站同一天都有净值（节假日后仍可准确更新）
- 风险筛选: 支持 `R1~R5` 与 `UNDEFINED`（未定义风险）组合筛选

**风险等级数据:**
- 自动来源: 中银理财官网 API (`bocwm.cn`)，覆盖中银理财自有产品 (2,082 个)，`source='bocwm'`
- 手动来源: 用户通过前端排行榜页面手动设置，`source='manual'`，支持任意产品
- 代销产品（招银/交银/信银/平安/工银/光大/华夏等）无法自动获取，可手动设置
  - 中国理财网 (chinawealth.com.cn) 有验证码+频率限制，无法批量抓取
  - 各代销机构官网无统一公开 API
- 不做推断，只用官方数据或用户手动设置
- BOCWM 分布: R1(716) / R2(1279) / R3(85) / R4(2)

**爬虫已知问题:**
- 偶发某天探测到总页数=1、抓取 0 条数据（可能是目标网站维护），但程序正常退出 code=0
- 每次全量抓取约 160 页 ~8000 行，耗时 70-80 秒，存在优化空间（增量抓取）
- 日志文件 `logs/task.log` 存在 GBK/UTF-8 编码混乱
