from DataManager import DataManager
from OliverVelezStrategy import OliverVelezStrategy
from BacktestEngine import BacktestEngine
from TradeVisualizer import TradeVisualizer

# 1. Fetch
#dm = DataManager(ticker="ES=F", filename="./data/ES_futures_data.tsf")
dm = DataManager(ticker="NQ=F", filename="./data/NQ_futures_data.tsf")

data = dm.fetch_and_clean()

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

