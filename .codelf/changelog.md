# Changelog

## [Unreleased]

### Added
- **Manual Portfolio Tracking**: Users can now manually add transaction records (Buy/Sell shares) via the "My Positions" page.
- **MyPositions View**: A new frontend view (`/my-positions`) to manage transactions and visualize daily income/total assets.
- **Income Calculation Engine**: `transactions.py` backend logic to simulate daily PnL based on historical transactions and NAV data.
    - Supports **Money Market Funds** (Income per 10k).
    - Supports **Net Value Products** (NAV difference).
    - **Fill-Forward Strategy**: Automatically fills missing NAV data (up to 15 days) to prevent asset curve "cliffs" on weekends or holidays.
    - **Hybrid Calculation**: Correctly handles products with missing `income_per_10k` fields by falling back to NAV difference logic.
- **Dashboard Integration**: Portfolio summary on the dashboard now automatically includes products from transaction records.

### Fixed
- **Income Discrepancy**: Fixed a critical bug where Net Value products were ignored in income calculation if they lacked `income_per_10k` data. Now correctly uses `cumulative_nav` difference.
- **Asset Drop**: Resolved an issue where total asset value dropped to zero on non-trading days by implementing a 15-day lookback for NAV data.
- **Project Structure**: Updated project documentation to reflect new modules (`transactions.py`, `MyPositions.vue`).

### Changed
- **Portfolio Logic**: `portfolio.py` now merges static `portfolio.json` codes with dynamic transaction codes for a unified view.
