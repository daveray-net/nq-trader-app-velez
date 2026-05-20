# /app/OliverVelezEngine.py

class OliverVelezEngine:
    # ─── SINGLE SOURCE OF TRUTH: STRATEGY CONFIGURATION CONSTANTS ───
    # These parameters establish Oliver's core institutional boundaries.
    ELEPHANT_MULT = 1.5   # Multiplier against ATR to define an institutional "Elephant Bar" (Ignition/Exhaustion)
    NARROW_LONG   = 3.0   # Long threshold: 20 MA & 200 MA must be tightly coiled ("The Narrow State")
    NARROW_SHORT  = 1.8   # Short threshold: Strict compression required to prevent shorting late drops
    STRETCH_LONG  = 4.0   # Long Extension: Absolute distance below 20 MA required for mean-reversion buyers
    STRETCH_SHORT = 3.5   # Short Extension: Absolute distance above 20 MA required to fade an upward run
    CONTRACT_SIZE = 7     # Topstep Combine size payload execution tier

    def __init__(self):
        # --- POSITION STATE MACHINE TRACKING ---
        self.stop_price = 0.0        # Protective floor/ceiling value assigned at trade execution
        self.entry_bar_size = 0.0     # Caches the explosive body range of the entry candle for exit filters
        self.is_added = False         # Color Game Tracking: Ensures you can only scale into a winner exactly once
        self.pushes = 0               # Momentum Counter: Tracks consecutive multi-bar expansion drives

        # --- STREAMING MEMORY STORAGE BUFFER ---
        # Natively caches the immediate past bar data to evaluate structure without array slicing delays
        self.p_open = None
        self.p_high = None
        self.p_low = None
        self.p_close = None
        self.p_sma20_high = None

        # --- NATIVE PIVOT BUFFER ---
        # Tracks local structural extremes to anchor protective stops dynamically during trade scaling
        self.last_swing_low = None
        self.last_swing_high = None

    def get_trade_attributes(self):
        """Yields parameters dynamically to configure the external Strategy wrapper."""
        return (
            self.ELEPHANT_MULT,
            self.NARROW_LONG,
            self.NARROW_SHORT,
            self.STRETCH_LONG,
            self.STRETCH_SHORT,
            self.CONTRACT_SIZE
        )

    def reset_position_state(self):
        """Wipes tracking properties on trade exits to cleanly reset the state machine for the next setup."""
        self.stop_price = 0.0
        self.entry_bar_size = 0.0
        self.is_added = False
        self.pushes = 0

    def process_bar(self, has_position: bool, is_long: bool, current_dt,
                    s20: float, s200: float, atr: float,
                    c_open: float, c_high: float, c_low: float, c_close: float):
        """
        100% Encapsulated Oliver Velez Trading Logic Engine.
        Processes a single live candle stream to issue strict, risk-insulated execution orders.
        """

        # --- PHASE 1: STREAM BUFFER WARM-UP ---
        # Ensures memory buffers are safely populated on historical startup or initial live stream connection
        if self.p_close is None:
            self.p_open, self.p_high, self.p_low, self.p_close = c_open, c_high, c_low, c_close
            self.p_sma20_high = c_high
            self.last_swing_low = c_low
            self.last_swing_high = c_high
            return 'HOLD', 0.0, None

        # --- PHASE 2: TRACK LOCAL STRUCTURAL EXTREMES ---
        # Dynamically logs minor swing high/low points to serve as dynamic cushions for Color Game additions
        if c_low < self.p_low:
            self.last_swing_low = c_low
        if c_high > self.p_high:
            self.last_swing_high = c_high

        # =====================================================================
        # CASE A: ACTIVE POSITION RISK & TRADE MANAGEMENT (EXITS & ADDS)
        # =====================================================================
        if has_position:
            position_type = 'LONG' if is_long else 'SHORT'

            # RULE 1: THE SESSION END CUT-OFF
            # Strict Topstep rule: Force close all open risk prior to the 4:00 PM NY Session Close
            if current_dt.hour >= 16:
                self.reset_position_state()
                self._update_history(c_open, c_high, c_low, c_close)
                return 'CLOSE', 0.0, None

            # RULE 2: THE HARD STOP PROTECTION
            # Capital preservation anchor: Immediate liquidation if the current wick violates the entry-bar floor/ceiling
            if (position_type == 'LONG' and c_low < self.stop_price) or \
               (position_type == 'SHORT' and c_high > self.stop_price):
                self.reset_position_state()
                self._update_history(c_open, c_high, c_low, c_close)
                return 'CLOSE', 0.0, None

            # RULE 3: INDEPENDENT LONG STRATUM EXITS
            if position_type == 'LONG':
                # THE 50% ELEPHANT BAR RETRACEMENT LOSS-CUTTER
                # Oliver's Core Rule: An institutional Elephant Bar should act as a wall.
                # If a current candle reverses and eats more than 50% of your entry bar's body, the ignition has failed.
                if abs(c_close - c_open) > (self.ELEPHANT_MULT * atr):
                    if abs(c_close - c_open) > abs(self.entry_bar_size * 0.5):
                        print(current_dt, ': retracement close')
                        self.reset_position_state()
                        self._update_history(c_open, c_high, c_low, c_close)
                        return 'CLOSE', 0.0, None

                # THE 20 MA CROSS OVER SLIDING EXIT
                # The 20 MA is your core trend backbone. If a long position fails to stay above the 20 MA line,
                # the microtrend bias has structurally shifted to bearish. Cut the position immediately.
                if c_close < s20:
                    self.reset_position_state()
                    self._update_history(c_open, c_high, c_low, c_close)
                    return 'CLOSE', 0.0, None

            # RULE 4: INDEPENDENT SHORT STRATUM EXITS
            else:
                # THE ANTI-WHIPSAW HIGHER HIGH RULE
                # If a short position faces an immediate counter-bar that takes out the high of the previous candle,
                # upward momentum is still aggressively printing. Close the short to prevent getting run over.
                if self.p_high < c_high:
                    print(current_dt, "short + higher highs: ", (self.p_high < c_high))
                    self.reset_position_state()
                    self._update_history(c_open, c_high, c_low, c_close)
                    return 'CLOSE', 0.0, None

                # Short 50% Retracement Rule: Liquidate if an upward move eats 50% of the short entry bar's body
                if abs(c_close - c_open) > (self.ELEPHANT_MULT * atr):
                    if abs(c_close - c_open) > abs(self.entry_bar_size * 0.5):
                        print(current_dt, ': retracement close')
                        self.reset_position_state()
                        self._update_history(c_open, c_high, c_low, c_close)
                        return 'CLOSE', 0.0, None

                # Short SMA20 Cross Rule: Liquidate if the short position closes completely above the 20 MA trendline
                if c_close > s20:
                    self.reset_position_state()
                    self._update_history(c_open, c_high, c_low, c_close)
                    return 'CLOSE', 0.0, None

            # RULE 5: THE 3-PUSH MOMENTUM EXHAUSTION EXIT
            # Oliver Velez's Core Extension Principle: The market moves in explosive bursts or "pushes".
            # If the current active position prints a 3rd distinct candle body expansion larger than 1.2 * ATR
            # in your trade's direction, momentum is mathematically exhausted. Harvest your maximum profits here.
            if abs(c_close - c_open) > (1.2 * atr):
                if (position_type == 'LONG' and c_close > c_open) or (position_type == 'SHORT' and c_close < c_open):
                    self.pushes += 1

            if self.pushes >= 3:
                self.reset_position_state()
                self._update_history(c_open, c_high, c_low, c_close)
                return 'CLOSE', 0.0, None

            # RULE 6: THE COLOR GAME SCALING-ADDITION MECHANISM
            # Oliver's Pyramiding Method: Never add to a loser; only add to clear, structural strength.
            # - For Longs: If a temporary red candle prints (p_close < p_open), buy the breakout the moment the
            #   current active green candle body takes out that red candle's high extreme (c_high > p_high).
            # - Move stop price tightly behind the last recorded swing extreme pivot for Topstep security.
            if not self.is_added:
                if position_type == 'LONG' and self.p_close < self.p_open and c_high > self.p_high:
                    self.is_added = True
                    self.stop_price = self.last_swing_low
                    self._update_history(c_open, c_high, c_low, c_close)
                    return 'BUY_ADD', self.stop_price, None
                elif position_type == 'SHORT' and self.p_close > self.p_open and c_low < self.p_low:
                    print(current_dt, "self.added=True")
                    self.is_added = True
                    self.stop_price = self.last_swing_high
                    self._update_history(c_open, c_high, c_low, c_close)
                    return 'SELL_ADD', self.stop_price, None

            self._update_history(c_open, c_high, c_low, c_close)
            return 'HOLD', self.stop_price, None

        # =====================================================================
        # CASE B: UNALLOCATED ENTRY ENGINE SELECTION
        # =====================================================================
        else:
            self.reset_position_state()

            long_body = c_close - c_open
            short_body = c_open - c_close
            gap = abs(s20 - s200)

            # ─── SECTION 1: MASTER LONG CRITERIA STRATUM ───
            # Oliver's Long Checklist:
            # 1. Elephant Bar: A candle whose body range commands the majority of current volatility (> 1.5 * ATR)
            # 2. The Narrow State: The 20 MA and 200 MA must be tightly compressed (< 3.0 * ATR), coiling energy.
            # 3. Location: The breakout candle close must cleanly validate above the maximum of both key moving averages.
            is_elephant_long = long_body > (self.ELEPHANT_MULT * atr)
            is_narrow_long = gap < (self.NARROW_LONG * atr)
            is_stretched_long = (s20 - c_close) > (self.STRETCH_LONG * atr) # Core Snapback Reversion Filter

            # TRIGGER 1A: THE INSTITUTIONAL BREAKOUT LONG
            if is_elephant_long and is_narrow_long and c_close > max(s20, s200):
                self.entry_bar_size = long_body
                self.stop_price = c_low - 0.25 # Place stop 1 tick below the breakout ignition candle floor
                self.pushes = 1
                self._update_history(c_open, c_high, c_low, c_close)
                return 'BUY_INITIAL', self.stop_price, 'BREAKOUT_LONG'

            # TRIGGER 1B: THE OVEREXTENDED SNAPBACK REVERSION LONG
            # Counter-trend entry: Price is drastically extended beneath a downward sloping 20 MA line.
            # Capitalize on institutional mean-reversion buying when an Elephant Bar snaps backward toward value.
            if is_elephant_long and is_stretched_long:
                self.entry_bar_size = long_body
                self.stop_price = c_low - 0.25
                self.pushes = 1
                self._update_history(c_open, c_high, c_low, c_close)
                return 'BUY_INITIAL', self.stop_price, 'SNAPBACK_LONG'

            # ─── SECTION 2: MASTER SHORT CRITERIA STRATUM ───
            # Oliver's Short Checklist:
            # 1. Bear Elephant Bar: Massive red breakdown candle range (> 1.5 * ATR)
            # 2. Narrow State Compression: Moving averages must be structurally packed together to ensure high energy.
            # 3. Anti-Chase Safeguard: To pass Combine rules, forbidden from shorting if price has fallen > 3.0 ATR from 200 MA.
            is_elephant_short = short_body > (self.ELEPHANT_MULT * atr)
            is_narrow_short = gap < (self.NARROW_SHORT * atr)
            is_extended_from_200 = (s200 - c_close) > (3.0 * atr) # The ultimate "Don't short the hole" safety shield
            is_stretched_above = (c_close - s20) > (self.STRETCH_SHORT * atr) # Overhead Snapback short filter

            # TRIGGER 2A: THE INSTITUTIONAL BREAKDOWN SHORT
            if is_elephant_short and is_narrow_short and c_close < min(s20, s200) and not is_extended_from_200:
                self.entry_bar_size = short_body
                self.stop_price = c_high + 0.25 # Place stop 1 tick above the breakdown ignition candle ceiling
                self.pushes = 1
                print(current_dt, "self.sell", 'BREAKOUT_SHORT')
                self._update_history(c_open, c_high, c_low, c_close)
                return 'SELL_INITIAL', self.stop_price, 'BREAKOUT_SHORT'

            # TRIGGER 22B: THE OVEREXTENDED SNAPBACK REVERSION SHORT
            # Counter-trend short: Price has surged aggressively overhead, stretching far away from the 20 MA trendline.
            # Step in to harvest a quick downside pullback back to the moving average mean.
            if is_elephant_short and is_stretched_above:
                self.entry_bar_size = short_body
                self.stop_price = c_high + 0.25
                self.pushes = 1
                print(current_dt, "self.sell", 'SNAPBACK_SHORT')
                self._update_history(c_open, c_high, c_low, c_close)
                return 'SELL_INITIAL', self.stop_price, 'SNAPBACK_SHORT'

            self._update_history(c_open, c_high, c_low, c_close)
            return 'HOLD', 0.0, None

    def _update_history(self, o, h, l, c):
        """Internal sliding memory pipeline. Shits active bar values into memory for next tick reference."""
        self.p_open = o
        self.p_high = h
        self.p_low = l
        self.p_close = c
