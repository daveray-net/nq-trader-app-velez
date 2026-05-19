import os
import pandas as pd
import yfinance as yf

class DataManager:
    def __init__(self, ticker="ES=F", filename="es_futures_data.tsv"):
        self.ticker = ticker
        self.filename = filename

    def fetch_and_clean(self, period="5d", interval="2m"):
        df = pd.DataFrame()
        if os.path.exists(self.filename):
            df = pd.read_csv(self.filename, sep='\t', index_col=0, parse_dates=True)
            # Ensure index is localized for comparison
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC').tz_convert('US/Eastern')

            last_ts = df.index[-1]
            print(f"Updating {self.ticker} from {last_ts}...")
            new_data = yf.download(self.ticker, start=last_ts, interval=interval, auto_adjust=True)

            if not new_data.empty:
                if isinstance(new_data.columns, pd.MultiIndex):
                    new_data.columns = new_data.columns.get_level_values(0)
                new_data.index = new_data.index.tz_convert('US/Eastern')
                new_data = new_data[new_data.index > last_ts]
                df = pd.concat([df, new_data])
                df.to_csv(self.filename, sep='\t')
        else:
            print(f"Downloading fresh history for {self.ticker}...")
            df = yf.download(self.ticker, period=period, interval=interval, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.index = df.index.tz_convert('US/Eastern')
            df.to_csv(self.filename, sep='\t')

        # Unified Pandas Cleanup
        df.columns = [col if isinstance(col, tuple) else col for col in df.columns]
        df = df.T.groupby(level=0).first().T.dropna()
        if 'Volume' in df.columns: df = df[df['Volume'] > 0]

        # Standardize for Backtesting Engine
        df.index = pd.to_datetime(df.index, utc=True).tz_convert('US/Eastern').tz_localize(None)
        df.index.name = 'Datetime'

        print(df)

        return df
