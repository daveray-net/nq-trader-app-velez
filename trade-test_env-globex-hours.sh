#!/usr/bin/env bash
set -e

echo "========================================="
echo " RUNNING OVERNIGHT GLOBEX WINDOW TEST     "
echo "========================================="

# Run backtest with localized overnight environment overrides
TRADING_START_DATE="2026-04-30" \
TRADING_END_DATE="2026-05-19" \
TRADING_TIME_START="23:00:00" \
TRADING_TIME_END="01:00:00" \
python main.py

echo "✅ Test completed. Verify all trades fall between 23:00 and 01:00."
