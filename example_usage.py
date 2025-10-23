"""
Example usage of ALPACA Trading Bot components

This file shows how to use various parts of the system programmatically.
"""

import pandas as pd
from datetime import datetime, timedelta

# Import components
from config import get_settings
from core.aster_client import AsterFuturesClient
from core.risk_manager import RiskManager
from strategies import (
    BreakoutScalpingStrategy,
    MomentumReversalStrategy,
    FundingArbitrageStrategy,
    LiquidationCascadeStrategy,
    MarketMakingStrategy
)
from backtesting import BacktestEngine
from bot import TradingBot


def example_1_test_api_connection():
    """Example: Test Aster API connection"""
    print("\n=== Example 1: Test API Connection ===\n")

    settings = get_settings()

    # Initialize client
    client = AsterFuturesClient(
        api_wallet=settings.aster_api_wallet_address,
        user_wallet=settings.aster_user_wallet_address,
        private_key=settings.aster_private_key
    )

    # Test connection
    try:
        info = client.get_exchange_info()
        print(f"✓ Connected to Aster successfully!")
        print(f"  Available symbols: {len(info.get('symbols', []))}")

        # Get BTC price
        ticker = client.get_ticker_price("BTCUSDT")
        print(f"  Current BTC price: ${ticker['price']}")

    except Exception as e:
        print(f"✗ Connection failed: {e}")


def example_2_strategy_analysis():
    """Example: Analyze market with a strategy"""
    print("\n=== Example 2: Strategy Analysis ===\n")

    settings = get_settings()
    client = AsterFuturesClient(
        api_wallet=settings.aster_api_wallet_address,
        user_wallet=settings.aster_user_wallet_address,
        private_key=settings.aster_private_key
    )

    # Get market data
    symbol = "BTCUSDT"
    klines = client.get_klines(symbol, "5m", 100)

    # Convert to DataFrame
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    # Initialize strategy
    strategy = BreakoutScalpingStrategy(leverage=30)

    # Analyze
    signal = strategy.analyze(df, symbol)

    if signal:
        print(f"✓ Signal generated for {symbol}!")
        print(f"  Action: {signal['action']}")
        print(f"  Entry: ${signal['entry_price']:.2f}")
        print(f"  Stop Loss: ${signal['stop_loss']:.2f}")
        print(f"  Take Profit: ${signal.get('take_profit', 'N/A')}")
        print(f"  Leverage: {signal['leverage']}x")
        print(f"  Confidence: {signal['confidence']:.2%}")
        print(f"  Reason: {signal['reason']}")
    else:
        print(f"✗ No signal at this time for {symbol}")


def example_3_risk_management():
    """Example: Risk management calculations"""
    print("\n=== Example 3: Risk Management ===\n")

    # Initialize risk manager
    risk_manager = RiskManager(
        initial_capital=10000,
        max_leverage=50,
        risk_per_trade=0.02,
        max_daily_loss=0.10,
        max_open_positions=5
    )

    # Example position parameters
    symbol = "BTCUSDT"
    entry_price = 50000
    stop_loss = 49000
    leverage = 30

    # Check if we can open position
    if risk_manager.can_open_position(symbol):
        print(f"✓ Can open position for {symbol}")

        # Calculate position size
        quantity = risk_manager.calculate_position_size(
            symbol,
            entry_price,
            stop_loss,
            leverage,
            volatility=0.02
        )

        print(f"  Position size: {quantity:.6f} BTC")
        print(f"  Position value: ${quantity * entry_price:.2f}")
        print(f"  Margin required: ${quantity * entry_price / leverage:.2f}")

        # Calculate liquidation price
        liq_price = risk_manager.calculate_liquidation_price(
            entry_price,
            leverage,
            "LONG"
        )

        print(f"  Liquidation price: ${liq_price:.2f}")
        print(f"  Distance to liquidation: {((entry_price - liq_price) / entry_price * 100):.2f}%")

        # Calculate take profit
        take_profit = risk_manager.calculate_take_profit(
            entry_price,
            stop_loss,
            "LONG",
            risk_reward_ratio=2.0
        )

        print(f"  Take profit (2:1 R/R): ${take_profit:.2f}")

        # Risk/Reward analysis
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
        print(f"  Risk: ${risk:.2f} ({risk/entry_price*100:.2f}%)")
        print(f"  Reward: ${reward:.2f} ({reward/entry_price*100:.2f}%)")
        print(f"  R/R Ratio: {reward/risk:.2f}:1")

    else:
        print(f"✗ Cannot open position for {symbol}")


def example_4_backtest_strategy():
    """Example: Backtest a single strategy"""
    print("\n=== Example 4: Backtest Strategy ===\n")

    settings = get_settings()
    client = AsterFuturesClient(
        api_wallet=settings.aster_api_wallet_address,
        user_wallet=settings.aster_user_wallet_address,
        private_key=settings.aster_private_key
    )

    # Fetch historical data
    symbol = "BTCUSDT"
    print(f"Fetching data for {symbol}...")

    klines = client.get_klines(symbol, "5m", 1000)

    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    print(f"Loaded {len(df)} candles")

    # Initialize strategy
    strategy = MomentumReversalStrategy(leverage=35)

    # Initialize backtest engine
    engine = BacktestEngine(
        initial_capital=10000,
        strategies=[strategy]
    )

    # Run backtest
    print(f"\nRunning backtest for {strategy.name}...")
    results = engine.run_backtest(df, symbol, strategy)

    # Print results
    print(f"\n=== Results ===")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    print(f"Total PnL: ${results['total_pnl']:.2f}")
    print(f"ROI: {results['roi']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")


def example_5_manual_trade():
    """Example: Execute a manual trade"""
    print("\n=== Example 5: Manual Trade (Demo) ===\n")

    print("⚠️  This is a DEMO - not executing real trade!")
    print("To execute real trades, use the TradingBot class or API.\n")

    settings = get_settings()

    # This would initialize a real client
    # client = AsterFuturesClient(...)

    # Manual trade parameters
    symbol = "BTCUSDT"
    side = "LONG"
    leverage = 20
    entry_price = 50000
    stop_loss = 49000
    take_profit = 52000

    print(f"Trade Setup:")
    print(f"  Symbol: {symbol}")
    print(f"  Side: {side}")
    print(f"  Entry: ${entry_price}")
    print(f"  Stop Loss: ${stop_loss}")
    print(f"  Take Profit: ${take_profit}")
    print(f"  Leverage: {leverage}x")

    # Calculate position size (demo)
    capital = 10000
    risk_per_trade = 0.02
    risk_amount = capital * risk_per_trade
    stop_distance = entry_price - stop_loss
    quantity = risk_amount / stop_distance

    print(f"\nPosition Sizing:")
    print(f"  Capital: ${capital}")
    print(f"  Risk per trade: {risk_per_trade*100}%")
    print(f"  Risk amount: ${risk_amount}")
    print(f"  Quantity: {quantity:.6f} BTC")
    print(f"  Position value: ${quantity * entry_price:.2f}")
    print(f"  Margin: ${quantity * entry_price / leverage:.2f}")

    # Real execution would be:
    # order = client.create_order(
    #     symbol=symbol,
    #     side="BUY" if side == "LONG" else "SELL",
    #     order_type="MARKET",
    #     quantity=quantity,
    #     leverage=leverage
    # )


def example_6_monitor_positions():
    """Example: Monitor positions via API"""
    print("\n=== Example 6: Monitor Positions ===\n")

    print("This example shows how to monitor positions via REST API")
    print("Make sure the API server is running: python run_api.py\n")

    print("Example API calls:\n")

    print("# Get all positions")
    print('curl "http://localhost:8000/positions" -H "X-API-Key: your_key"\n')

    print("# Get specific position")
    print('curl "http://localhost:8000/positions/BTCUSDT" -H "X-API-Key: your_key"\n')

    print("# Get statistics")
    print('curl "http://localhost:8000/statistics" -H "X-API-Key: your_key"\n')

    print("# Get trade history")
    print('curl "http://localhost:8000/trades?limit=10" -H "X-API-Key: your_key"\n')

    print("See README.md for complete API documentation.")


def main():
    """Run all examples"""
    print("="*60)
    print("ALPACA Trading Bot - Example Usage")
    print("="*60)

    examples = [
        ("Test API Connection", example_1_test_api_connection),
        ("Strategy Analysis", example_2_strategy_analysis),
        ("Risk Management", example_3_risk_management),
        ("Backtest Strategy", example_4_backtest_strategy),
        ("Manual Trade Demo", example_5_manual_trade),
        ("Monitor Positions", example_6_monitor_positions),
    ]

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")

    print("\n0. Run all examples")
    print("q. Quit")

    choice = input("\nSelect example (0-6): ").strip()

    if choice == 'q':
        return

    if choice == '0':
        for name, func in examples:
            try:
                func()
            except Exception as e:
                print(f"\n✗ Error in {name}: {e}")
            input("\nPress Enter to continue...")
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        try:
            examples[int(choice)-1][1]()
        except Exception as e:
            print(f"\n✗ Error: {e}")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
