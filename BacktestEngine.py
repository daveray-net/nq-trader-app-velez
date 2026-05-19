import pandas as pd
from backtesting import Backtest
import os

class BacktestEngine:
    def __init__(self, data, strategy_class, cash=250000, commission=0.0002):
        self.bt = Backtest(data, strategy_class, cash=cash, commission=commission)
        self.data = data
        self.stats = None

    def run(self):
        self.stats = self.bt.run()
        return self.stats

    def analyze(self, run_dir=None):
        """Analyzes results and saves the trade log to the run directory."""
        if self.stats is not None:
            print("\n" + "="*30)
            print(" PERFORMANCE STATISTICS ")
            print("="*30)
            print(self.stats)

            # Generate the trade log DataFrame
            log_df = self.get_formatted_log()
            print("\n" + "="*30)
            print(" COMPREHENSIVE TRADE LOG ")
            print("="*30)
            print(log_df.to_string(index=False))

            # SAVE TO CSV
            if run_dir:
                csv_path = os.path.join(run_dir, 'trade_log.csv')
                log_df.to_csv(csv_path, index=False)
                print(f"\nTrade log saved to: {csv_path}")

    def get_formatted_log(self):
        trades = self.stats._trades
        if trades.empty:
            return pd.DataFrame()

        log_df = trades[['EntryTime', 'ExitTime', 'Size', 'EntryPrice', 'ExitPrice', 'PnL', 'ReturnPct']].copy()
        log_df['Side'] = log_df['Size'].apply(lambda x: 'LONG' if x > 0 else 'SHORT')
        log_df['Return%'] = (log_df['ReturnPct'] * 100).round(2)
        log_df['PnL'] = log_df['PnL'].round(2)
        log_df['TotalPnL'] = log_df['PnL'].cumsum().round(2)

        return log_df[['EntryTime', 'ExitTime', 'Side', 'EntryPrice', 'ExitPrice', 'PnL', 'Return%', 'TotalPnL']]



