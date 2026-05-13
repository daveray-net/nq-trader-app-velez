import os
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime

class TradeVisualizer:
    def __init__(self, base_dir='./data//trades'):
        # Create the timestamped path: trades/2026-05-04-14h30m05s
        date_str = datetime.now().strftime("%Y-%m-%d-%Hh%Mm%Ss")
        self.run_dir = os.path.join(base_dir, date_str)

        if not os.path.exists(self.run_dir):
            os.makedirs(self.run_dir)
        print(f"Visualizer initialized. Run directory: {self.run_dir}")

    @property
    def get_run_dir(self):
        return self.run_dir


    def plot_velez_trades(self, data, stats, start_time=None, end_time=None,
                          sma20_full=None, sma200_full=None, save_name=None, trade_info=None):
        df = data.copy()
        if start_time: df = df[df.index >= pd.to_datetime(start_time)]
        if end_time:   df = df[df.index <= pd.to_datetime(end_time)]
        if df.empty: return

        apds = []
        if sma20_full is not None:
            apds.append(mpf.make_addplot(sma20_full.loc[df.index], color='orange', width=1.0))
        if sma200_full is not None:
            apds.append(mpf.make_addplot(sma200_full.loc[df.index], color='blue', width=1.0))

        # --- RESTORED ALINES & MARKER LOGIC ---
        entry_l, entry_s = pd.Series(index=df.index, dtype=float), pd.Series(index=df.index, dtype=float)
        exit_p, exit_l = pd.Series(index=df.index, dtype=float), pd.Series(index=df.index, dtype=float)
        alines_lines = []
        alines_colors = []

        for _, trade in stats._trades.iterrows():
            # Check if trade is within plot window
            if (start_time is None or trade['EntryTime'] >= pd.to_datetime(start_time)) and \
               (end_time is None or trade['ExitTime'] <= pd.to_datetime(end_time)):

                # Setup Markers
                if trade['Size'] > 0: entry_l.loc[trade['EntryTime']] = trade['EntryPrice']
                else:                 entry_s.loc[trade['EntryTime']] = trade['EntryPrice']

                if trade['PnL'] > 0:  exit_p.loc[trade['ExitTime']] = trade['ExitPrice']
                else:                 exit_l.loc[trade['ExitTime']] = trade['ExitPrice']

                # Setup Vectors (Dashed lines connecting entry to exit)
                alines_lines.append([(trade['EntryTime'], trade['EntryPrice']), (trade['ExitTime'], trade['ExitPrice'])])
                alines_colors.append('green' if trade['PnL'] > 0 else 'red')

        # Add Scatters to apds
        if entry_l.notna().any(): apds.append(mpf.make_addplot(entry_l, type='scatter', marker='^', color='green', markersize=100))
        if entry_s.notna().any(): apds.append(mpf.make_addplot(entry_s, type='scatter', marker='v', color='red', markersize=100))
        if exit_p.notna().any():  apds.append(mpf.make_addplot(exit_p, type='scatter', marker='x', color='green', markersize=120))
        if exit_l.notna().any():  apds.append(mpf.make_addplot(exit_l, type='scatter', marker='x', color='red', markersize=120))

        # --- PLOTTING ---
        fig, axlist = mpf.plot(df, type='candle', style='charles', figsize=(16, 10),
                                addplot=apds, returnfig=True,
                                alines=dict(alines=alines_lines, colors=alines_colors, alpha=0.6, linewidths=2),
                                title=f"Velez Strategy Analysis", ylabel='Price',
                                warn_too_much_data=len(df) + 1)

        main_ax = axlist[0]

        main_ax.legend(['20 SMA (Orange)', '200 SMA (Blue)'], loc='upper right')

        if trade_info:
            # Format text into a single horizontal line to fit the top margin
            stats_text = (f"EntryTime: {trade_info['EntryTime']}  |  "
                          f"Side: {trade_info['Side']}  |  "
                          f"Result: {trade_info['Result']}  |  "
                          f"PnL: ${trade_info['PnL']:.2f}  |  "
                          f"Return: {trade_info['ReturnPct']:.2f}%  |  "
                          f"Duration: {trade_info['Duration']}")

            # y=1.05 moves the box slightly above the top of the chart
            # x=0.5 + ha='center' centers it under the title
            props = dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='gray')
            main_ax.text(0.5, 1.05, stats_text, transform=main_ax.transAxes,
                         fontsize=10, fontweight='bold', verticalalignment='bottom',
                         horizontalalignment='center', bbox=props)

                # ... [Previous Legend logic] ...

##        main_ax.legend(['20 SMA (Orange)', '200 SMA (Blue)'], loc='upper right')

##        if trade_info:
##            stats_text = (f"Result: {trade_info['Result']}\n"
##                          f"PnL: ${trade_info['PnL']:.2f}\n"
##                          f"Return: {trade_info['ReturnPct']:.2f}%\n"
##                          f"Duration: {trade_info['Duration']}")
##            props = dict(boxstyle='round', facecolor='white', alpha=0.8)
##            main_ax.text(0.02, 0.95, stats_text, transform=main_ax.transAxes,
##                           fontsize=11, verticalalignment='top', bbox=props)


        # ... [Save logic] ...
        if save_name:
            save_path = os.path.join(self.run_dir, save_name)
            plt.savefig(save_path)
            plt.close(fig)

    def generate_plots(self, data, stats):
        sma20_f = data['Close'].rolling(20).mean()
        sma200_f = data['Close'].rolling(200).mean()

        # Overall Summary
        self.plot_velez_trades(data, stats, sma20_full=sma20_f, sma200_full=sma200_f, save_name='overall_trades.png')

#         log_df['Side'] = log_df['Size'].apply(lambda x: 'LONG' if x > 0 else 'SHORT')
        # Individual Trades
        for i, trade in stats._trades.iterrows():
            start = trade['EntryTime'] - pd.Timedelta(hours=2)
            end = trade['ExitTime'] + pd.Timedelta(minutes=30)
            side='LONG'
            if(trade['Size'] < 0):
                side = 'SHORT'
            t_info = {
                'EntryTime': trade['EntryTime'],
                'Side': side,
                'Result': 'PROFIT' if trade['PnL'] > 0 else 'LOSS',
                'PnL': trade['PnL'],
                'ReturnPct': trade['ReturnPct'] * 100,
                'Duration': trade['ExitTime'] - trade['EntryTime']
            }

            self.plot_velez_trades(data, stats, start_time=start, end_time=end,
                                   sma20_full=sma20_f, sma200_full=sma200_f,
                                   save_name=f'trade_{i+1}.png', trade_info=t_info)
