# Changelog

## [Unreleased]

### Added
- **Portfolio Enhancements**:
    - **NAV Increment**: Portfolio cards now display the daily NAV change (`day_nav_change`) with color-coded indicators (Red/Green).
    - **Auto-Calculated Metrics**: For Net Value products lacking official fields:
        - **Annualized 7D**: Automatically estimated by looking back 4-10 days in history.
        - **Income per 10k**: Automatically simulated based on daily NAV increment.
- **Manual Portfolio Tracking**: Users can now manually add transaction records (Buy/Sell shares) via the "My Positions" page.
- **MyPositions View**: A new frontend view (`/my-positions`) to manage transactions and visualize daily income/total assets.
- **Income Calculation Engine**: `transactions.py` backend logic to simulate daily PnL based on historical transactions and NAV data.
    - Supports **Money Market Funds** (Income per 10k).
    - Supports **Net Value Products** (NAV difference).
    - **Fill-Forward Strategy**: Automatically fills missing NAV data (up to 15 days) to prevent asset curve "cliffs" on weekends or holidays.
    - **Hybrid Calculation**: Correctly handles products with missing `income_per_10k` fields by falling back to NAV difference logic.
- **Dashboard Integration**: Portfolio summary on the dashboard now automatically includes products from transaction records.
- **Lockup Period Parsing**: Frontend API now derives lockup period text/days from product name keywords.

### Fixed
- **Income Discrepancy**: Fixed a critical bug where Net Value products were ignored in income calculation if they lacked `income_per_10k` data. Now correctly uses `cumulative_nav` difference.
- **Asset Drop**: Resolved an issue where total asset value dropped to zero on non-trading days by implementing a 15-day lookback for NAV data.
- **Project Structure**: Updated project documentation to reflect new modules (`transactions.py`, `MyPositions.vue`).
- **Advanced Ranking**: Fixed incorrect import path that prevented `/api/ranking/advanced` from working, and added unit NAV fallback for period return calculation.
- **Product History**: Use latest available NAV date as the window anchor for history queries.
- **Routing**: Registered product history routes so Advanced Ranking can load trends.

### Changed
- **Portfolio Logic**: `portfolio.py` now merges static `portfolio.json` codes with dynamic transaction codes for a unified view.
- **Cleanup**: Removed hardcoded default products from `portfolio.json` to show only user-specific holdings.
- **Advanced Ranking**: Backend now合并风险等级并返回区间天数，前端展示风险、区间与净值指标。
- **Deployment Path**: Project runtime path has been switched from `/opt/bocfound` to `/opt/bocfund` with compatibility symlink preserved.

## [Recent Fixes & Enhancements]

### Fixed
- **Lockup Period Parsing** (`api/index.ts` — `parseLockupPeriod()`):
    - Now correctly identifies 11+ name patterns: 日开 / 日日开 / 每日开放, Chinese-numeral months (三个月持有), parenthesized period (（9个月）最短持有期, （1年）最短持有期 with embedded spaces), keyword±digits in both orders, and fallback digit scan when lockup keyword is present.
    - **Exclusion**: 月月开 / 季季开 / 开放式 are redemption frequency terms, NOT treated as lockup periods.
    - Added pattern for 最低持有 (e.g. 7天最低持有 → 7天).

### Added
- **Advanced Ranking — Lockup Filter "未定义期限"**: Added an "未定义期限" option to the lockup period filter, allowing users to isolate products whose names contain no parseable lockup period.
- **Advanced Ranking — Pagination**: Table now renders 100 rows per page with full prev/next/page-number controls; rank indices continue correctly across pages. Resolves browser lag when displaying thousands of products.
