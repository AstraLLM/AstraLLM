"""
ALPACA Trading Bot - Main Entry Point
"""
import sys
import argparse
from loguru import logger

from config import get_settings
from bot import TradingBot


def setup_logging():
    """Configure logging"""
    settings = get_settings()

    # Remove default logger
    logger.remove()

    # Console logger
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.log_level
    )

    # File logger
    if settings.log_to_file:
        logger.add(
            "logs/alpaca_{time}.log",
            rotation="1 day",
            retention="7 days",
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
        )


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description="ALPACA Trading Bot")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
        help="Trading symbols (e.g., BTCUSDT ETHUSDT SOLUSDT BNBUSDT)"
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=None,
        help="Enabled strategies (e.g., breakout_scalping momentum_reversal)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Iteration interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run in backtest mode instead of live trading"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (simulate trading without real orders)"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    logger.info("="*60)
    logger.info("ALPACA Trading Bot - High Leverage Trading System")
    logger.info("="*60)

    if args.backtest:
        logger.info("Running in BACKTEST mode")
        run_backtest(args.symbols)
    elif args.dry_run:
        logger.info("Running in DRY-RUN mode (Paper Trading)")
        run_live(args.symbols, args.strategies, args.interval, dry_run=True)
    else:
        logger.info("Running in LIVE mode")
        run_live(args.symbols, args.strategies, args.interval, dry_run=False)


def run_live(symbols, strategies, interval, dry_run=False):
    """Run live trading"""

    logger.info(f"Initializing bot with symbols: {symbols}")

    # Initialize bot
    bot = TradingBot(symbols=symbols, enabled_strategies=strategies, dry_run=dry_run)

    logger.info(f"Active strategies: {[s.name for s in bot.strategies]}")

    if dry_run:
        logger.warning("🔶 DRY-RUN MODE: All trades are simulated, no real orders! 🔶")

    # Start bot
    bot.start(interval_seconds=interval)


def run_backtest(symbols):
    """Run backtesting"""

    from backtesting import BacktestEngine
    from strategies import (
        BreakoutScalpingStrategy,
        MomentumReversalStrategy,
        FundingArbitrageStrategy,
        LiquidationCascadeStrategy,
        MarketMakingStrategy
    )
    from core.aster_client import AsterFuturesClient
    from config import get_settings
    import pandas as pd

    settings = get_settings()

    logger.info("Initializing backtest engine...")

    # Initialize strategies
    strategies = [
        BreakoutScalpingStrategy(leverage=30),
        MomentumReversalStrategy(leverage=35),
        FundingArbitrageStrategy(leverage=20),
        LiquidationCascadeStrategy(leverage=45),
        MarketMakingStrategy(leverage=20)
    ]

    # Initialize backtest engine
    engine = BacktestEngine(
        initial_capital=settings.backtest_initial_capital,
        strategies=strategies
    )

    # Initialize client for fetching historical data
    client = AsterFuturesClient(
        api_key=settings.aster_api_key,
        api_secret=settings.aster_api_secret,
        signer_address=settings.aster_signer_address,
        user_address=settings.aster_user_wallet_address,
        private_key=settings.aster_private_key
    )

    for symbol in symbols:
        logger.info(f"\nFetching historical data for {symbol}...")

        try:
            # Fetch historical data (last 1000 candles)
            klines = client.get_klines(symbol, "5m", 1000)

            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

            logger.info(f"Loaded {len(df)} candles for {symbol}")

            # Get funding history
            funding_history = client.get_funding_rate(symbol, limit=100)

            # Run backtest
            results = engine.run_multi_strategy_backtest(df, symbol, funding_history)

            # Save results
            engine.save_results(results, f"backtest_results_{symbol}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json")

        except Exception as e:
            logger.error(f"Error backtesting {symbol}: {e}")


if __name__ == "__main__":
    main()
