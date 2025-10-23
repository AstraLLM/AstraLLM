"""
Run backtesting
"""
import sys
sys.path.insert(0, '.')

from main import setup_logging, run_backtest

if __name__ == "__main__":
    setup_logging()

    # Run backtest on these symbols
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    run_backtest(symbols)
