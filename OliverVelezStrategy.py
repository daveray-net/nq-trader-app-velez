import pandas as pd
import numpy as np
from backtesting import Strategy
import os

# MASTER SWITCHES
START_HOUR = int(os.getenv('TRADING_START_HOUR', 9))
START_MIN  = int(os.getenv('TRADING_START_MIN', 30))
END_HOUR   = int(os.getenv('TRADING_END_HOUR', 16))
END_MIN    = int(os.getenv('TRADING_END_MIN', 0))

class OliverVelezStrategy(Strategy):
    # Asymmetrical Parameters for independent tuning
    elephant_mult = 1.5

    # Long Tuning (The 'Gold' logic you want to keep)
    narrow_long  = 3.0
    stretch_long = 4.0

    # Short Tuning (Strict 'Creme' logic to stop chasing)
    narrow_short  = 1.8
    stretch_short = 3.5

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

    def get_long_facts(self):
        s20, s200, atr = self.sma20[-1], self.sma200[-1], self.atr[-1]
        c_close, c_open, c_low = self.data.Close[-1], self.data.Open[-1], self.data.Low[-1]
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

    def get_short_facts(self):
        s20, s200, atr = self.sma20[-1], self.sma200[-1], self.atr[-1]
        c_close, c_open, c_high = self.data.Close[-1], self.data.Open[-1], self.data.High[-1]
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



##    def get_long_facts(self):
##        """Pure Bullish Logic - Tuned for Breakouts & Snap-backs."""
##        s20, s200, atr = self.sma20[-1], self.sma200[-1], self.atr[-1]
##        c_close, c_open, c_low = self.data.Close[-1], self.data.Open[-1], self.data.Low[-1]
##        body = c_close - c_open
##        gap = abs(s20 - s200)

##        is_elephant = body > (self.elephant_mult * atr)
##        is_narrow = gap < (self.narrow_long * atr)
##        is_stretched = (s20 - c_close) > (self.stretch_long * atr)

##        # Signal A: Narrow Breakout
##        is_breakout = is_elephant and is_narrow and c_close > max(s20, s200)
##        # Signal B: Wide Snap-back
##        is_snapback = is_elephant and is_stretched

##        if is_breakout: return 'BREAKOUT_LONG', c_low - 0.25
##        if is_snapback: return 'SNAPBACK_LONG', c_low - 0.25
##        return None, 0

##    def get_short_facts(self):
##        """Pure Bearish Logic - Stricter 'Creme de la Creme' only."""
##        s20, s200, atr = self.sma20[-1], self.sma200[-1], self.atr[-1]
##        c_close, c_open, c_high = self.data.Close[-1], self.data.Open[-1], self.data.High[-1]
##        body = c_open - c_close # Red Bar
##        gap = abs(s20 - s200)

##        is_elephant = body > (self.elephant_mult * atr)
##        is_narrow = gap < (self.narrow_short * atr) # Stricter coil

##        # ANTI-CHASE: If we are already 3.5 ATRs below the 200 SMA, do NOT breakout
##        is_extended_from_200 = (s200 - c_close) > (3.5 * atr)
##        is_stretched_above = (c_close - s20) > (self.stretch_short * atr)

##        # Signal A: Narrow Breakout (Only if NOT extended/chasing)
##        is_breakout = is_elephant and is_narrow and c_close < min(s20, s200) and not is_extended_from_200
##        # Signal B: Wide Snap-back
##        is_snapback = is_elephant and is_stretched_above

##        if is_breakout: return 'BREAKOUT_SHORT', c_high + 0.25
##        if is_snapback: return 'SNAPBACK_SHORT', c_high + 0.25
##        return None, 0

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
        t = self.data.index[-1]
        curr_time_val = t.hour * 100 + t.minute
        in_window = (START_HOUR * 100 + START_MIN) <= curr_time_val <= (END_HOUR * 100 + END_MIN)

        # --- 1. POSITION MANAGEMENT ---
        if self.position:
            if t.hour >= 16: self.position.close(); return

            c_low, c_high, c_close, c_open = self.data.Low[-1], self.data.High[-1], self.data.Close[-1], self.data.Open[-1]
            p_close, p_open, p_high, p_low = self.data.Close[-2], self.data.Open[-2], self.data.High[-2], self.data.Low[-2]

            # Hard Stop
            if (self.position.is_long and c_low < self.stop_price) or \
               (self.position.is_short and c_high > self.stop_price):
                self.position.close(); return

             # short and making higher highs...
            if ( self.position.is_short and ( self.data.High[-2] < self.data.High[-1] ) ):
                print( t, "short + higher highs: ", (self.data.High[-2] < self.data.High[-1]) )
                self.position.close(); return

            # try and exit near the high, ** early exit on first pullback **...
            #if ( self.position.is_long and self.data.High[-1] > self.data.High[-2] ):
            #    if ( (abs(self.data.Open[-2] - self.data.Close[-2])) > (self.atr ) ):
            #        print(t, "YES",  self.atr[-1], abs(self.data.Open[-1] - self.data.Close[-1]), self.data.Low[-1] )
            #        self.stop_price = self.data.Low[-1]
            #        #self.position.close()
            #        return

            # if the current candle is retracing the previous elephant candle by more than 50% then exit
            if ( abs(self.data.Close[-1] - self.data.Open[-1]) > (self.elephant_mult * self.atr[-1]) ):
                if ( abs(self.data.Close[-1] - self.data.Open[-1]) > abs(self.entry_bar_size * 0.5) ):
                    print( t,': retracement close')
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
                    print(t, "self.added=True")
                    self.sell(size= round(self.size / 2) ); self.added = True; self.stop_price = ( self.getPreviousHigh() )

            # 3-Push Exit
            if abs(c_close - c_open) > (1.2 * self.atr[-1]):
                if (self.position.is_long and c_close > c_open) or (self.position.is_short and c_close < c_open):
                    self.pushes += 1
            if self.pushes >= 3: self.position.close(); return


        # --- 2. ENTRY ENGINE ---
        else:
            if in_window:
                l_tag, l_stop = self.get_long_facts()
                s_tag, s_stop = self.get_short_facts()

                if l_tag:
                    self.stop_price = l_stop
                    self.buy(size=self.size, tag=l_tag)
                    self.added, self.pushes = False, 1
                elif s_tag:
                    self.stop_price = s_stop
                    print(t,"self.sell",s_tag)
                    self.sell(size=self.size, tag=s_tag)
                    self.added, self.pushes = False, 1

