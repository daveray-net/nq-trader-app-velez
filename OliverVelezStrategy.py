# /app/OliverVelezStrategy.py
import pandas as pd
import numpy as np
from backtesting import Strategy
import os
from OliverVelezEngine import OliverVelezEngine

class OliverVelezStrategy(Strategy):
    elephant_mult = None
    narrow_long = None
    narrow_short = None
    stretch_long = None
    stretch_short = None
    size = None

    def init(self):
        """Sets up indicator arrays and maps Single-Source properties from the Engine."""
        super().init()
        self.engine = OliverVelezEngine()

        (self.elephant_mult,
         self.narrow_long,
         self.narrow_short,
         self.stretch_long,
         self.stretch_short,
         self.size) = self.engine.get_trade_attributes()

        self.sma20 = self.I(lambda x: pd.Series(x).rolling(20).mean(), self.data.Close)
        self.sma200 = self.I(lambda x: pd.Series(x).rolling(200).mean(), self.data.Close)

        def get_atr(H, L, C):
            H, L, C = pd.Series(H), pd.Series(L), pd.Series(C)
            tr = pd.concat([(H-L), (H-C.shift()).abs(), (L-C.shift()).abs()], axis=1).max(axis=1)
            return tr.rolling(14).mean()
        self.atr = self.I(get_atr, self.data.High, self.data.Low, self.data.Close)

        self.added, self.pushes, self.stop_price = False, 0, 0

        # Hoist Environment Window Constraints (FIXED WITH singular element lookups)
        default_start_date = self.data.df.index[0]
        default_end_date = self.data.df.index[-1]
        env_start_date = os.environ.get("TRADING_START_DATE")
        env_end_date = os.environ.get("TRADING_END_DATE")
        self._start_date_bound = pd.to_datetime(env_start_date) if env_start_date else default_start_date
        self._end_date_bound = pd.to_datetime(env_end_date) if env_end_date else default_end_date

        self._time_start_bound = pd.Timestamp(os.environ.get("TRADING_TIME_START", "09:30:00")).time()
        self._time_end_bound = pd.Timestamp(os.environ.get("TRADING_TIME_END", "16:00:00")).time()

    def is_in_trading_window(self, current_datetime) -> bool:
        is_within_date_range = self._start_date_bound <= current_datetime <= self._end_date_bound
        current_time_of_day = current_datetime.time()
        if self._time_start_bound <= self._time_end_bound:
            is_within_time_window = self._time_start_bound <= current_time_of_day <= self._time_end_bound
        else:
            is_within_time_window = current_time_of_day >= self._time_start_bound or current_time_of_day <= self._time_end_bound
        return bool(is_within_date_range and is_within_time_window)

    def getPreviousLow(self):
        i = -1
        low = self.data.Low[-1]
        while low >= self.data.Low[-1]:
            low = self.data.Low[i]
            i = (i - 1)
        return low

    def getPreviousHigh(self):
        i = -1
        high = self.data.High[-1]
        while high <= self.data.High[-1]:
            high = self.data.High[i]
            i = (i - 1)
        return high

    def next(self):
        current_dt = self.data.index[-1]

        if not self.is_in_trading_window(current_dt):
            if self.position:
                self.position.close()
                self.engine.reset_position_state()
            return

        # ⚡ FIXED DATA PIPELINE: Forwards finder functions directly to support Color Game trail stops
        action, stop_price, tag = self.engine.process_bar(
            has_position=bool(self.position),
            is_long=bool(self.position.is_long if self.position else False),
            current_dt=current_dt,
            s20=self.sma20[-1],
            s200=self.sma200[-1],
            atr=self.atr[-1],
            c_open=self.data.Open[-1],
            c_high=self.data.High[-1],
            c_low=self.data.Low[-1],
            c_close=self.data.Close[-1],
            prev_high_finder_func=self.getPreviousHigh,
            prev_low_finder_func=self.getPreviousLow
        )

        if action == 'CLOSE':
            self.position.close()
        elif action == 'BUY_INITIAL':
            self.stop_price = stop_price
            self.buy(size=self.size, tag=tag)
            self.added, self.pushes = False, 1
        elif action == 'SELL_INITIAL':
            self.stop_price = stop_price
            self.sell(size=self.size, tag=tag)
            self.added, self.pushes = False, 1
        elif action == 'BUY_ADD':
            self.buy(size=round(self.size / 2))
            self.stop_price = stop_price # Captures true getPreviousLow calculated float
        elif action == 'SELL_ADD':
            self.sell(size=round(self.size / 2))
            self.stop_price = stop_price # Captures true getPreviousHigh calculated float
