from Environment import Environment
from TSConnector import TSConnector
from DataManager import DataManager
from OliverVelezStrategy import OliverVelezStrategy
from BacktestEngine import BacktestEngine
from TradeVisualizer import TradeVisualizer

# 1. Fetch the unified system environment config object
env = Environment.getEnvironment()

## 2. Routing Flow Execution
try:
    print(f"filename={env.data_file}")

    if env.live_trading:
        print(f"live_trading={env.live_trading}")
        # TSConnector projectx data
        connector = TSConnector(data_file_path=env.data_file)
        data = connector.get_bars(bar_limit=500)

    else:
        print(f"ticker={env.yf_ticker}")
        # DataManager yfinance data
        dm = DataManager(ticker=env.yf_ticker, filename=env.data_file)
        data = dm.fetch_and_clean()

    # 3. Data verified! Ready for strategy processing loops
    print(f"\n[SUCCESS] Loaded {len(data)} bars safely into operational memory space.")
    print(data.tail(5))

except Exception as err:
    print(f"\n[CRITICAL ERROR ON INITIALIZATION]: {err}")
    sys.exit(1)

# 1. Fetch
#dm = DataManager(ticker="ES=F", filename="./data/ES_futures_data.tsf")
#dm = DataManager(ticker="NQ=F", filename="./data/NQ_futures_data.tsf")
#data = dm.fetch_and_clean()

# 2. Backtest
engine = BacktestEngine(data, OliverVelezStrategy)
stats = engine.run()

# 2. Initialize Visualizer and get its run directory
viz = TradeVisualizer()
run_path = viz.get_run_dir

# 3. Analyze and Save Log (Passing the path)
engine.analyze(run_dir=run_path)

# 4. Generate Plots
viz.generate_plots(data, stats)

