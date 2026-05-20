import pandas as pd
import numpy as np
from backtesting import Strategy
import os

# MASTER SWITCHES
# set environment variables
# export TRADING_END_DATE="2026-05-13"
# export TRADING_START_DATE="2026-05-12"
# export TRADING_TIME_END="16:00:00"
# export TRADING_TIME_START="18:00:00"
#
# remove environmnet variables
# unset TRADING_END_DATE
# unset TRADING_START_DATE
# unset TRADING_TIME_END
# unset TRADING_TIME_START


class OliverVelezStrategy(Strategy):
    # Asymmetrical Parameters for independent tuning
    elephant_mult = 1.5

    # Long Tuning (The 'Gold' logic you want to keep)
    narrow_long  = 3.0
    stretch_long = 4.0

    # Short Tuning (Strict 'Creme' logic to stop chasing)
    narrow_short  = 1.8
    stretch_short = 3.5

    #number of contracts
    size = 7


    def init(self):
        super().init()
        self.sma20 = self.I(lambda x: pd.Series(x).rolling(20).mean(), self.data.Close)
        self.sma200 = self.I(lambda x: pd.Series(x).rolling(200).mean(), self.data.Close)

        def get_atr(H, L, C):
            H, L, C = pd.Series(H), pd.Series(L), pd.Series(C)
            tr = pd.concat([(H-L), (H-C.shift()).abs(), (L-C.shift()).abs()], axis=1).max(axis=1)
            return tr.rolling(14).mean()

        self.atr = self.I(get_atr, self.data.High, self.data.Low, self.data.Close)
        self.added, self.pushes, self.stop_price = False, 0, 0
        self.entry_bar_size=0

        # --- HOISTED ENVIRONMENT DATE LOOKUPS (RUNS ONCE) ---
        default_start_date = self.data.df.index[0]
        default_end_date = self.data.df.index[-1]

        env_start_date = os.environ.get("TRADING_START_DATE")
        env_end_date = os.environ.get("TRADING_END_DATE")

        self._start_date_bound = pd.to_datetime(env_start_date) if env_start_date else default_start_date
        self._end_date_bound = pd.to_datetime(env_end_date) if env_end_date else default_end_date

        # --- HOISTED ENVIRONMENT TIME LOOKUPS (RUNS ONCE) ---
        default_time_start = pd.Timestamp("09:30:00").time()
        default_time_end = pd.Timestamp("16:00:00").time()

        env_time_start = os.environ.get("TRADING_TIME_START")
        env_time_end = os.environ.get("TRADING_TIME_END")

        self._time_start_bound = pd.Timestamp(env_time_start).time() if env_time_start else default_time_start
        self._time_end_bound = pd.Timestamp(env_time_end).time() if env_time_end else default_time_end


    def is_in_trading_window(self, current_datetime) -> bool:

        # Fast comparison using pre-calculated bounds
        is_within_date_range = self._start_date_bound <= current_datetime <= self._end_date_bound

        current_time_of_day = current_datetime.time()
        if self._time_start_bound <= self._time_end_bound:
            is_within_time_window = self._time_start_bound <= current_time_of_day <= self._time_end_bound
        else:
            is_within_time_window = current_time_of_day >= self._time_start_bound or current_time_of_day <= self._time_end_bound

        return bool(is_within_date_range and is_within_time_window)

    def get_long_facts(self, s20, s200, atr, c_close, c_open, c_low):
        # ⚡ PASSIVE LOOKUPS: No array indexing math is performed inside this block
        body = c_close - c_open
        gap = abs(s20 - s200)

        is_elephant = body > (self.elephant_mult * atr)
        is_narrow = gap < (self.narrow_long * atr)
        # Sligthly tighter stretch to catch that 13:56 reversal
        is_stretched = (s20 - c_close) > (3.5 * atr)

        if is_elephant and is_narrow and c_close > max(s20, s200):
            self.entry_bar_size = body
            return 'BREAKOUT_LONG', c_low - 0.25
        if is_elephant and is_stretched:
            self.entry_bar_size = body
            return 'SNAPBACK_LONG', c_low - 0.25
        return None, 0

    def get_short_facts(self, s20, s200, atr, c_close, c_open, c_high):
        # ⚡ PASSIVE LOOKUPS: Perfect for standard WebSocket live data streams
        body = c_open - c_close
        gap = abs(s20 - s200)

        is_elephant = body > (self.elephant_mult * atr)
        is_narrow = gap < (self.narrow_short * atr)

        # Guard against shorting 'The Hole'
        is_extended_from_200 = (s200 - c_close) > (3.0 * atr)
        is_stretched_above = (c_close - s20) > (3.5 * atr)

        if is_elephant and is_narrow and c_close < min(s20, s200) and not is_extended_from_200:
            self.entry_bar_size = body
            return 'BREAKOUT_SHORT', c_high + 0.25
        if is_elephant and is_stretched_above:
            self.entry_bar_size = body
            return 'SNAPBACK_SHORT', c_high + 0.25
        return None, 0

    def getPreviousLow(self):
        i=-1
        low = self.data.Low[-1]
        while ( low >= self.data.Low[-1] ) :
            low = self.data.Low[i]; i = (i-1)
        return low

    def getPreviousHigh(self):
        i=-1
        high = self.data.High[-1]
        while ( high <= self.data.High[-1] ) :
            high = self.data.High[i]; i = (i-1)
        return high


    def next(self):
        # 1. Capture the single current datetime stamp
        current_dt = self.data.index[-1]

        # 2. Extract values for the active candle EXACTLY ONCE per loop
        # This completely stops expensive multi-layered index looking backwards ([-1])
        close_val = self.data.Close[-1]
        open_val = self.data.Open[-1]
        high_val = self.data.High[-1]
        low_val = self.data.Low[-1]

        s20_val = self.sma20[-1]
        s200_val = self.sma200[-1]
        atr_val = self.atr[-1]

        c_low, c_high, c_close, c_open = self.data.Low[-1], self.data.High[-1], self.data.Close[-1], self.data.Open[-1]
        p_close, p_open, p_high, p_low = self.data.Close[-2], self.data.Open[-2], self.data.High[-2], self.data.Low[-2]

        # 3. Handle Exits
        # --- 1. POSITION MANAGEMENT ---

        # end of nysession close...
        if self.position:
            if current_dt.hour >= 16:
                self.position.close()
                return

            # ... execute your remaining trailing stop management rules ...

            # Hard Stop
            if (self.position.is_long and c_low < self.stop_price) or \
               (self.position.is_short and c_high > self.stop_price):
                self.position.close(); return

             # short and making higher highs...
            if ( self.position.is_short and ( self.data.High[-2] < self.data.High[-1] ) ):
                print(current_dt, "short + higher highs: ", (self.data.High[-2] < self.data.High[-1]) )
                self.position.close(); return

            # try and exit near the high, ** early exit on first pullback **...
            #if ( self.position.is_long and self.data.High[-1] > self.data.High[-2] ):
            #    if ( (abs(self.data.Open[-2] - self.data.Close[-2])) > (self.atr ) ):
            #        print(current_dt, "YES",  self.atr[-1], abs(self.data.Open[-1] - self.data.Close[-1]), self.data.Low[-1] )
            #        self.stop_price = self.data.Low[-1]
            #        #self.position.close()
            #        return

            # if the current candle is retracing the previous elephant candle by more than 50% then exit
            if ( abs(self.data.Close[-1] - self.data.Open[-1]) > (self.elephant_mult * self.atr[-1]) ):
                if ( abs(self.data.Close[-1] - self.data.Open[-1]) > abs(self.entry_bar_size * 0.5) ):
                    print(current_dt,': retracement close')
                    self.position.close(); return

            # exit if current candle close crosses above or below the sma20 ...
            if ( self.position.is_long and self.data.Close[-1] < self.sma20[-1] ) or \
                ( self.position.is_short and self.data.Close[-1] > self.sma20[-1] ):
                self.position.close(); return


            # Color Game Add
            if not self.added:
                if self.position.is_long and p_close < p_open and c_high > p_high:
                    self.buy(size= round(self.size / 2) ); self.added = True; self.stop_price = ( self.getPreviousLow() )
                elif self.position.is_short and p_close > p_open and c_low < p_low:
                    print(current_dt, "self.added=True")
                    self.sell(size= round(self.size / 2) ); self.added = True; self.stop_price = ( self.getPreviousHigh() )

            # 3-Push Exit
            if abs(c_close - c_open) > (1.2 * self.atr[-1]):
                if (self.position.is_long and c_close > c_open) or (self.position.is_short and c_close < c_open):
                    self.pushes += 1
            if self.pushes >= 3: self.position.close(); return


        # --- 2. ENTRY ENGINE ---
        else:
            if self.is_in_trading_window(current_dt):
                # Pass pre-extracted scalar values into your facts functions
                l_tag, l_stop = self.get_long_facts(s20_val, s200_val, atr_val, close_val, open_val, low_val)
                s_tag, s_stop = self.get_short_facts(s20_val, s200_val, atr_val, close_val, open_val, high_val)

                if l_tag:
                    self.stop_price = l_stop
                    self.buy(size=self.size, tag=l_tag)
                    self.added, self.pushes = False, 1
                elif s_tag:
                    self.stop_price = s_stop
                    print(current_dt,"self.sell",s_tag)
                    self.sell(size=self.size, tag=s_tag)
                    self.added, self.pushes = False, 1

