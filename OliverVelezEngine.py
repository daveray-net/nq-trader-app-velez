# /app/OliverVelezEngine.py

class OliverVelezEngine:
    # ─── SINGLE SOURCE OF TRUTH: STRATEGY CONFIGURATION CONSTANTS ───
    ELEPHANT_MULT = 1.5   # Multiplier against ATR to define an institutional "Elephant Bar"
    NARROW_LONG   = 3.0   # Long threshold: 20 MA & 200 MA must be tightly coiled ("The Narrow State")
    NARROW_SHORT  = 1.8   # Short threshold: Strict compression required to prevent shorting late drops
    STRETCH_LONG  = 4.0   # Long Extension: Absolute distance below 20 MA required for mean-reversion buyers
    STRETCH_SHORT = 3.5   # Short Extension: Absolute distance above 20 MA required to fade an upward run
    CONTRACT_SIZE = 7     # Topstep Combine size payload execution tier

    def __init__(self):
        # --- POSITION STATE MACHINE TRACKING ---
        self.stop_price = 0.0
        self.entry_bar_size = 0.0
        self.is_added = False
        self.pushes = 0

        # --- STREAMING MEMORY STORAGE BUFFER ---
        self.p_open = None
        self.p_high = None
        self.p_low = None
        self.p_close = None

        # --- NATIVE PIVOT BUFFER ---
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
        """Wipes tracking properties on trade exits to cleanly reset the state machine."""
        self.stop_price = 0.0
        self.entry_bar_size = 0.0
        self.is_added = False
        self.pushes = 0

    def process_bar(self, has_position: bool, is_long: bool, current_dt,
                    s20: float, s200: float, atr: float,
                    c_open: float, c_high: float, c_low: float, c_close: float,
                    prev_high_finder_func=None, prev_low_finder_func=None):
        # 🛠️ FIXED PARAMETER SIGNATURE
        """
        100% Encapsulated Oliver Velez Trading Logic Engine.
        Processes a single live candle stream to issue strict, risk-insulated execution orders.
        """

        ######### begin input parameter debug info
        print(f"\n[ENGINE-IN] >>> Entering process_bar for Datetime: {current_dt} <<<")
        print(f"  [Position State]  Has Position: {has_position} | Is Long: {is_long}")
        print(f"  [Moving Averages] 20 MA: {s20:.2f} | 200 SMA: {s200:.2f} | ATR: {atr:.2f}")
        print(f"  [Candle Metrics]  Open: {c_open:.2f} | High: {c_high:.2f} | Low: {c_low:.2f} | Close: {c_close:.2f}")
        print(f"  [Helper Funcs]    Has High Finder: {prev_high_finder_func is not None} | Has Low Finder: {prev_low_finder_func is not None}")
        print("-" * 50)
        ######### end input parameter debug info
        ######### begin temporary attribute mapper
        print("\n[DIAGNOSTIC] Listing all active engine properties:")
        engine_attributes = [attr for attr in dir(self) if not attr.startswith('__') and not callable(getattr(self, attr))]
        print(f"  Available Engine Variables: {engine_attributes}")
        ######### end temporary attribute mapper

        # --- PHASE 1: STREAM BUFFER WARM-UP ---
        if self.p_close is None:
            self.p_open, self.p_high, self.p_low, self.p_close = c_open, c_high, c_low, c_close
            self.last_swing_low = c_low
            self.last_swing_high = c_high
            return 'HOLD', 0.0, None

        # --- PHASE 2: TRACK LOCAL STRUCTURAL EXTREMES ---
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
            if current_dt.hour >= 16:
                self.reset_position_state()
                self._update_history(c_open, c_high, c_low, c_close)
                return 'CLOSE', 0.0, None

            # RULE 2: THE HARD STOP PROTECTION
            if (position_type == 'LONG' and c_low < self.stop_price) or \
               (position_type == 'SHORT' and c_high > self.stop_price):
                self.reset_position_state()
                self._update_history(c_open, c_high, c_low, c_close)
                return 'CLOSE', 0.0, None

            # RULE 3: INDEPENDENT LONG STRATUM EXITS
            if position_type == 'LONG':
                # THE 50% ELEPHANT BAR RETRACEMENT LOSS-CUTTER
                if abs(c_close - c_open) > (self.ELEPHANT_MULT * atr):
                    if abs(c_close - c_open) > abs(self.entry_bar_size * 0.5):
                        print(current_dt, ': retracement close')
                        self.reset_position_state()
                        self._update_history(c_open, c_high, c_low, c_close)
                        return 'CLOSE', 0.0, None

                # THE 20 MA CROSS OVER SLIDING EXIT
                if c_close < s20:
                    self.reset_position_state()
                    self._update_history(c_open, c_high, c_low, c_close)
                    return 'CLOSE', 0.0, None

            # RULE 4: INDEPENDENT SHORT STRATUM EXITS
            else:
                # THE ANTI-WHIPSAW HIGHER HIGH RULE
                if self.p_high < c_high:
                    print(current_dt, "short + higher highs: ", (self.p_high < c_high))
                    self.reset_position_state()
                    self._update_history(c_open, c_high, c_low, c_close)
                    return 'CLOSE', 0.0, None

                # Short 50% Retracement Rule
                if abs(c_close - c_open) > (self.ELEPHANT_MULT * atr):
                    if abs(c_close - c_open) > abs(self.entry_bar_size * 0.5):
                        print(current_dt, ': retracement close')
                        self.reset_position_state()
                        self._update_history(c_open, c_high, c_low, c_close)
                        return 'CLOSE', 0.0, None

                # Short SMA20 Cross Rule
                if c_close > s20:
                    self.reset_position_state()
                    self._update_history(c_open, c_high, c_low, c_close)
                    return 'CLOSE', 0.0, None

            # RULE 5: THE 3-PUSH MOMENTUM EXHAUSTION EXIT
            if abs(c_close - c_open) > (1.2 * atr):
                if (position_type == 'LONG' and c_close > c_open) or (position_type == 'SHORT' and c_close < c_open):
                    self.pushes += 1

            if self.pushes >= 3:
                self.reset_position_state()
                self._update_history(c_open, c_high, c_low, c_close)
                return 'CLOSE', 0.0, None

            # RULE 6: THE COLOR GAME SCALING-ADDITION MECHANISM
            if not self.is_added:
                if position_type == 'LONG' and self.p_close < self.p_open and c_high > self.p_high:
                    self.is_added = True
                    self.stop_price = prev_low_finder_func() if prev_low_finder_func else self.last_swing_low
                    self._update_history(c_open, c_high, c_low, c_close)
                    return 'BUY_ADD', self.stop_price, None
                elif position_type == 'SHORT' and self.p_close > self.p_open and c_low < self.p_low:
                    print(current_dt, "self.added=True")
                    self.is_added = True
                    self.stop_price = prev_high_finder_func() if prev_high_finder_func else self.last_swing_high
                    self._update_history(c_open, c_high, c_low, c_close)
                    return 'SELL_ADD', self.stop_price, None

            self._update_history(c_open, c_high, c_low, c_close)
            return 'HOLD', self.stop_price, None

        # ---------------------------------------------------------------------
        # CASE B: UNALLOCATED ENTRY ENGINE SELECTION
        # ---------------------------------------------------------------------
        else:
            self.reset_position_state()

            long_body = c_close - c_open
            short_body = c_open - c_close
            gap = abs(s20 - s200)

            # ─── SECTION 1: MASTER LONG CRITERIA STRATUM ───
            is_elephant_long = long_body > (self.ELEPHANT_MULT * atr)
            is_narrow_long = gap < (self.NARROW_LONG * atr)
            is_stretched_long = (s20 - c_close) > (self.STRETCH_LONG * atr)

            # TRIGGER 1A: THE INSTITUTIONAL BREAKOUT LONG
            if is_elephant_long and is_narrow_long and c_close > max(s20, s200):
                self.entry_bar_size = long_body
                self.stop_price = c_low - 0.25
                self.pushes = 1
                self._update_history(c_open, c_high, c_low, c_close)
                return 'BUY_INITIAL', self.stop_price, 'BREAKOUT_LONG'

            # TRIGGER 1B: THE OVEREXTENDED SNAPBACK REVERSION LONG
            if is_elephant_long and is_stretched_long:
                self.entry_bar_size = long_body
                self.stop_price = c_low - 0.25
                self.pushes = 1
                self._update_history(c_open, c_high, c_low, c_close)
                return 'BUY_INITIAL', self.stop_price, 'SNAPBACK_LONG'

            # ─── SECTION 2: MASTER SHORT CRITERIA STRATUM ───
            is_elephant_short = short_body > (self.ELEPHANT_MULT * atr)
            is_narrow_short = gap < (self.NARROW_SHORT * atr)
            is_extended_from_200 = (s200 - c_close) > (3.0 * atr)
            is_stretched_above = (c_close - s20) > (self.STRETCH_SHORT * atr)

            # TRIGGER 2A: THE INSTITUTIONAL BREAKDOWN SHORT
            if is_elephant_short and is_narrow_short and c_close < min(s20, s200) and not is_extended_from_200:
                self.entry_bar_size = short_body
                self.stop_price = c_high + 0.25
                self.pushes = 1
                print(current_dt, "self.sell", 'BREAKOUT_SHORT')
                self._update_history(c_open, c_high, c_low, c_close)
                return 'SELL_INITIAL', self.stop_price, 'BREAKOUT_SHORT'

            # TRIGGER 2B: THE OVEREXTENDED SNAPBACK REVERSION SHORT
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
        self.p_open = o
        self.p_high = h
        self.p_low = l
        self.p_close = c
