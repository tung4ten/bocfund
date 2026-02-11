#!/usr/bin/env bash
# ============================================================
# 每日定时任务：抓取净值数据 + 同步风险等级（全量模式覆盖）
# crontab: 0 8 * * * /opt/bocfound/fund/cron_scrape.sh
# (UTC 08:00 = 北京时间 16:00)
# ============================================================
set -euo pipefail

PROJECT_DIR="/opt/bocfound"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/cron_scrape.log"
PYTHON="/usr/bin/python3"

mkdir -p "${LOG_DIR}"

{
    echo "========================================"
    echo "[$(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S')] 定时任务开始"
    echo "========================================"

    # 1. 抓取净值数据 + 风险等级增量同步（cli.py 默认行为）
    cd "${PROJECT_DIR}"
    ${PYTHON} -m fund.boc_scraper.cli

    echo ""
    echo "[$(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S')] 增量同步完成，开始全量风险等级同步..."

    # 2. 全量风险等级同步（BOCWM 有值→覆盖，无值→保留 manual）
    ${PYTHON} -m fund.boc_scraper.sync_risk_levels --full

    echo ""
    echo "[$(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S')] 定时任务完成"
    echo "========================================"
    echo ""

} >> "${LOG_FILE}" 2>&1
