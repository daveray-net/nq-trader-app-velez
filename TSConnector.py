# data/TSConnector.py
import json
import os
import subprocess
import pandas as pd
from datetime import datetime, timedelta

class TSConnector:
    def __init__(self, data_file_path):
        self.script_path = "projectx/retrieve-bars.curl"
        self.data_file_path = data_file_path
        self.interval_minutes = 2

    def get_bars(self, bar_limit=300):
        print(f"\n[DEBUG] [TSConnector] Checking local file system for up-to-date data...")

        # 1. CLEAN PRE-FLIGHT CHECK (Zero text-parsing or string hacking)
        if os.path.exists(self.data_file_path):
            try:
                # Read file identically to your DataManager
                existing_df = pd.read_csv(self.data_file_path, sep='\t', index_col=0, parse_dates=True)

                if not existing_df.empty:
                    # Align timezone using your exact DataManager logic
                    if existing_df.index.tz is None:
                        existing_df.index = existing_df.index.tz_localize('UTC').tz_convert('US/Eastern')

                    # Grab the last timestamp object directly
                    last_ts = existing_df.index[-1]

                    # Target floor math: Match current candle floor in Eastern time
                    now_eastern = datetime.utcnow().replace(tzinfo=pd.Timestamp('UTC').tz).tz_convert('US/Eastern')
                    current_candle_floor = now_eastern.replace(
                        minute=(now_eastern.minute // self.interval_minutes) * self.interval_minutes,
                        second=0, microsecond=0
                    )

                    print(f"[DEBUG] [TSConnector] Newest file timestamp: {last_ts}")
                    print(f"[DEBUG] [TSConnector] Expected candle floor:    {current_candle_floor}")

                    # Direct object comparison - clean, reliable, and warning-free
                    if last_ts >= current_candle_floor:
                        print(f"[SUCCESS] [TSConnector] Data up to date! SKIPPING network call.")
                        df_out = existing_df.tail(bar_limit).copy()
                        df_out.index = df_out.index.tz_localize(None)
                        df_out.index.name = 'Datetime'
                        return df_out

            except Exception as cache_err:
                print(f"[WARN] [TSConnector] Cache check skipped due to alignment: {cache_err}")

        # 2. CACHE MISS: Fetch new live data via curl script
        df_new = self._fetch_from_api()

        # 3. SAFE APPEND AND UPDATE ON DISK
        self._append_live_data_safely(df_new)

        # 4. STANDARD UNIFIED DATAMANAGER CLEANUP
        df_final = df_new.tail(bar_limit).copy()
        df_final.index = pd.to_datetime(df_final.index, utc=True).tz_convert('US/Eastern').tz_localize(None)
        df_final.index.name = 'Datetime'

        return df_final

    def _fetch_from_api(self):
        result = subprocess.run([self.script_path], capture_output=True, text=True, check=True)
        raw_output = result.stdout.strip()

        if not raw_output.startswith("{"):
            json_start = raw_output.find("{")
            if json_start != -1:
                raw_output = raw_output[json_start:]

        data = json.loads(raw_output)
        bars = data["bars"][::-1] # Reverse to oldest first

        rows = []
        for bar in bars:
            utc_dt = datetime.fromisoformat(bar["t"].replace("+00:00", ""))
            local_dt = utc_dt - timedelta(hours=4)
            formatted_dt = f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')}-04:00"

            rows.append({
                "Datetime": formatted_dt,
                "Close": round(bar["c"], 2),
                "High": round(bar["h"], 2),
                "Low": round(bar["l"], 2),
                "Open": round(bar["o"], 2),
                "Volume": int(bar["v"])
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df.set_index("Datetime", inplace=True)

        print(f"returning DataFrame: {df}")
        return df

    def _append_live_data_safely(self, live_df):
        if live_df.empty:
            return

        if os.path.exists(self.data_file_path):
            existing_df = pd.read_csv(self.data_file_path, sep="\t", index_col="Datetime")
            combined_df = pd.concat([existing_df, live_df])
        else:
            combined_df = live_df

        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
        combined_df.sort_index(inplace=True)
        combined_df.to_csv(self.data_file_path, sep="\t")
        print(f"[DEBUG] [TSConnector] File synchronized cleanly. Total rows on disk: {len(combined_df)}")
