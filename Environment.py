# Environment.py
import os

class Environment:
    def __init__(self):
        # 1. Parse boolean environment flags safely
        self.live_trading = os.environ.get("LIVE_TRADING", "false").lower() in ("true", "1")

        # 2. Read ticker and safely isolate the asset root token (e.g. "NQ=F" -> "NQ")
        self.yf_ticker = os.environ.get("TICKER", "NQ=F")
        self.root_symbol = self.yf_ticker.split("=")[0]

        # 3. Dynamically construct your uniform file path string automatically
        self.data_file = os.environ.get("DATA_FILE", f"data/{self.root_symbol}_futures_data.tsf")

        # 4. Grab other required core API parameters
        self.contract_id = os.environ.get("CONTRACT_ID")
        self.api_session_token = os.environ.get("API_SESSION_TOKEN")

    @classmethod
    def getEnvironment(cls):
        """Static factory method to quickly instantiate and return the active configuration."""
        return cls()
