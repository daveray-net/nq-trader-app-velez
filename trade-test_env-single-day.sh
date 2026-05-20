#!/usr/bin/env bash
set -e

echo "========================================="
echo " RUNNING SINGLE DAY RANGE BOUNDARY TEST   "
echo "========================================="

# Run backtest with localized single-day environment overrides
TRADING_START_DATE="2026-05-04" \
TRADING_END_DATE="2026-05-05" \
TRADING_TIME_START="09:30:00" \
TRADING_TIME_END="16:00:00" \
python main.py

echo "✅ Test completed. Verify only May 4th trades are present."
