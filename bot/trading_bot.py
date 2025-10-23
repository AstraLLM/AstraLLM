"""
Main Trading Bot with Live Execution
"""
import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from loguru import logger

from core.aster_client import AsterFuturesClient
from core.risk_manager import RiskManager
from core.strategy_selector import StrategySelector
from core.market_regime import MarketRegime
from core.bot_state import BotStateManager
from strategies import (
    BreakoutScalpingStrategy,
    MomentumReversalStrategy,
    FundingArbitrageStrategy,
    LiquidationCascadeStrategy,
    MarketMakingStrategy,
    OrderFlowImbalanceStrategy,
    VWAPReversionStrategy,
    SupportResistanceBounceStrategy
)
from config import get_settings


class TradingBot:
    """
    Main Trading Bot

    Features:
    - Multi-strategy execution
    - Real-time market data processing
    - Automated position management
    - Risk management
    - Performance tracking
    """

    def __init__(self, symbols: List[str], enabled_strategies: Optional[List[str]] = None, dry_run: bool = False, use_dynamic_selector: bool = True):
        self.settings = get_settings()
        self.dry_run = dry_run
        self.use_dynamic_selector = use_dynamic_selector

        if self.dry_run:
            logger.warning("🔶 DRY-RUN MODE ENABLED - No real orders will be executed! 🔶")

        # Initialize Aster client
        self.client = AsterFuturesClient(
            api_key=self.settings.aster_api_key,
            api_secret=self.settings.aster_api_secret,
            signer_address=self.settings.aster_signer_address,
            user_address=self.settings.aster_user_wallet_address,
            private_key=self.settings.aster_private_key
        )

        # Trading pairs
        self.symbols = symbols

        # Initialize risk manager
        self.risk_manager = RiskManager(
            initial_capital=self.settings.backtest_initial_capital,
            max_leverage=self.settings.max_leverage,
            risk_per_trade=self.settings.risk_per_trade,
            max_daily_loss=self.settings.max_daily_loss,
            max_open_positions=self.settings.max_open_positions
        )

        # Initialize strategies
        self.strategies = self._init_strategies(enabled_strategies)

        # Initialize dynamic strategy selector
        if self.use_dynamic_selector:
            self.strategy_selector = StrategySelector(self.strategies)
            logger.info("🎯 Dynamic Strategy Selector ENABLED - Bot will auto-select best strategy per market regime")
        else:
            self.strategy_selector = None
            logger.info("📊 Using static strategy selection")

        # State management
        self.is_running = False
        self.last_update = {}
        self.current_regime = MarketRegime.UNKNOWN
        self.selected_strategy_name = None

        # Initialize persistent state manager
        self.state_manager = BotStateManager(db_path="data/bot_state.db")

        # Initialize balance tracking (CRITICAL for accurate PnL)
        self._init_balance_tracking()

        # Sync existing positions from exchange
        self.sync_positions_from_exchange()

        # Clean up any orphaned SL/TP orders
        self.cleanup_orphan_orders()

        logger.info(f"TradingBot initialized with {len(self.symbols)} symbols and {len(self.strategies)} strategies")

    def _init_balance_tracking(self):
        """
        Initialize balance tracking - CRITICAL for accurate PnL calculation

        On first run: Fetches real balance from Aster and saves as initial_balance
        On subsequent runs: Uses saved initial_balance from database
        """
        try:
            # Check if we already have an initial balance saved
            saved_initial_balance = self.state_manager.get_initial_balance()

            if saved_initial_balance is not None:
                # We have a saved initial balance - use it
                logger.info(f"📊 Using saved initial balance from DB: ${saved_initial_balance:.2f}")
                logger.info(f"   First run was at: {self.state_manager.get_first_run_timestamp()}")
            else:
                # First run ever - fetch current balance from Aster and save it
                logger.info("🔥 FIRST RUN DETECTED - Initializing balance tracking...")

                # Use account endpoint to get totalWalletBalance (most accurate)
                account_data = self.client.get_account_info()

                # Get totalWalletBalance from account info (this is the real equity)
                current_balance = float(account_data.get('totalWalletBalance', 0))

                logger.info(f"📊 Fetched real balance from Aster API:")
                logger.info(f"   totalWalletBalance: ${current_balance:.2f}")

                # Save as initial balance
                self.state_manager.set_initial_balance(current_balance)

                logger.info(f"💾 Initial balance saved: ${current_balance:.2f}")
                logger.info(f"   All future PnL will be calculated from this baseline")

        except Exception as e:
            logger.error(f"❌ Error initializing balance tracking: {e}")
            logger.warning(f"⚠️  Falling back to env initial_capital: ${self.settings.backtest_initial_capital}")

    def _init_strategies(self, enabled_strategies: Optional[List[str]]) -> List:
        """Initialize enabled strategies"""

        all_strategies = {
            'breakout_scalping': BreakoutScalpingStrategy(leverage=20),
            'momentum_reversal': MomentumReversalStrategy(leverage=25),
            'funding_arbitrage': FundingArbitrageStrategy(leverage=20),
            'liquidation_cascade': LiquidationCascadeStrategy(leverage=45),
            'market_making': MarketMakingStrategy(leverage=15),
            # NEW TOP 3 STRATEGIES
            'order_flow_imbalance': OrderFlowImbalanceStrategy(leverage=20),
            'vwap_reversion': VWAPReversionStrategy(leverage=15),
            'support_resistance': SupportResistanceBounceStrategy(leverage=20)
        }

        # Filter based on settings
        strategies = []

        if self.settings.enable_breakout_scalping:
            strategies.append(all_strategies['breakout_scalping'])

        if self.settings.enable_momentum_reversal:
            strategies.append(all_strategies['momentum_reversal'])

        if self.settings.enable_funding_arbitrage:
            strategies.append(all_strategies['funding_arbitrage'])

        if self.settings.enable_liquidation_cascade:
            strategies.append(all_strategies['liquidation_cascade'])

        if self.settings.enable_market_making:
            strategies.append(all_strategies['market_making'])

        # NEW TOP 3 STRATEGIES
        if self.settings.enable_order_flow_imbalance:
            strategies.append(all_strategies['order_flow_imbalance'])

        if self.settings.enable_vwap_reversion:
            strategies.append(all_strategies['vwap_reversion'])

        if self.settings.enable_support_resistance:
            strategies.append(all_strategies['support_resistance'])

        # Additional filter if specific strategies provided
        if enabled_strategies:
            strategies = [s for s in strategies if s.name.lower().replace(' ', '_') in enabled_strategies]

        return strategies

    def sync_positions_from_exchange(self):
        """
        Sync positions from Aster exchange on bot startup
        This allows the bot to recover state after restart
        """
        try:
            logger.info("🔄 Syncing positions from Aster exchange...")

            # Get all open positions from Aster
            positions = self.client.get_position_info()

            synced_count = 0
            for pos in positions:
                symbol = pos['symbol']
                position_amt = float(pos.get('positionAmt', 0))

                # Skip if no position
                if position_amt == 0:
                    continue

                # Extract position data
                entry_price = float(pos.get('entryPrice', 0))
                mark_price = float(pos.get('markPrice', entry_price))
                leverage = int(pos.get('leverage', 20))
                unrealized_pnl = float(pos.get('unRealizedProfit', 0))
                liquidation_price = float(pos.get('liquidationPrice', 0))

                # Determine side
                side = "LONG" if position_amt > 0 else "SHORT"
                quantity = abs(position_amt)

                # Calculate approximate stop loss and take profit
                # (we don't know the original values, so we estimate based on position)
                if side == "LONG":
                    # SL typically 1-2% below entry
                    stop_loss = entry_price * 0.985
                    # TP typically 1-2% above entry
                    take_profit = entry_price * 1.015
                else:
                    stop_loss = entry_price * 1.015
                    take_profit = entry_price * 0.985

                # Try to fetch existing SL/TP orders for this symbol
                sl_order_id = None
                tp_order_id = None
                try:
                    open_orders = self.client.get_open_orders(symbol)
                    for order in open_orders:
                        order_type = order.get('type', '')
                        if order_type == 'STOP_MARKET':
                            sl_order_id = str(order.get('orderId', ''))
                            logger.info(f"  🔍 Found existing SL order: {sl_order_id}")
                        elif order_type == 'TAKE_PROFIT_MARKET':
                            tp_order_id = str(order.get('orderId', ''))
                            logger.info(f"  🔍 Found existing TP order: {tp_order_id}")
                except Exception as e:
                    logger.debug(f"Could not fetch open orders for {symbol}: {e}")

                # Recreate position in risk manager
                logger.info(f"  📊 Recovering position: {side} {quantity} {symbol} @ ${entry_price} (Leverage: {leverage}x, PnL: ${unrealized_pnl:.2f})")

                # Manually create position object in risk manager
                from core.risk_manager import Position
                from datetime import datetime
                position = Position(
                    symbol=symbol,
                    side=side,
                    entry_price=entry_price,
                    quantity=quantity,
                    leverage=leverage,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    liquidation_price=liquidation_price,
                    unrealized_pnl=unrealized_pnl,
                    entry_time=datetime.now(),  # We don't know the actual entry time
                    strategy="recovered",  # Mark as recovered from exchange
                    sl_order_id=sl_order_id,  # Save SL order ID if found
                    tp_order_id=tp_order_id   # Save TP order ID if found
                )

                # Add to risk manager
                self.risk_manager.positions[symbol] = position
                synced_count += 1

            if synced_count > 0:
                logger.info(f"✅ Successfully synced {synced_count} position(s) from exchange")
            else:
                logger.info("ℹ️  No open positions found on exchange")

        except Exception as e:
            logger.error(f"❌ Error syncing positions from exchange: {e}")
            logger.warning("⚠️  Bot will start with empty position state")

    def cleanup_orphan_orders(self):
        """
        Clean up orphaned SL/TP orders that don't have corresponding open positions
        This is critical for safety - prevents spurious orders from executing unexpectedly
        """
        try:
            logger.info("🧹 Checking for orphaned orders...")

            # Get all open positions from exchange
            positions = self.client.get_position_info()

            # Create set of symbols with active positions
            active_positions = set()
            for pos in positions:
                position_amt = float(pos.get('positionAmt', 0))
                if position_amt != 0:
                    active_positions.add(pos['symbol'])

            # Get all open orders
            all_orders = self.client.get_open_orders()  # No symbol = get all orders

            orphaned_orders = []
            for order in all_orders:
                symbol = order.get('symbol')
                order_type = order.get('type', '')
                order_id = order.get('orderId', '')

                # Check if this is a SL/TP order
                if order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET']:
                    # If order exists but no position → orphaned order
                    if symbol not in active_positions:
                        orphaned_orders.append({
                            'symbol': symbol,
                            'order_id': order_id,
                            'type': order_type,
                            'side': order.get('side', 'UNKNOWN'),
                            'price': float(order.get('stopPrice', 0))
                        })

            # Cancel orphaned orders
            if orphaned_orders:
                logger.warning(f"⚠️  Found {len(orphaned_orders)} orphaned order(s)!")

                for orphan in orphaned_orders:
                    try:
                        if not self.dry_run:
                            self.client.cancel_order(orphan['symbol'], order_id=orphan['order_id'])
                            logger.info(f"✅ Canceled orphaned {orphan['type']} order: "
                                      f"{orphan['symbol']} {orphan['side']} @ ${orphan['price']} "
                                      f"(Order ID: {orphan['order_id']})")
                        else:
                            logger.info(f"[DRY-RUN] Would cancel orphaned {orphan['type']} order: "
                                      f"{orphan['symbol']} {orphan['side']} @ ${orphan['price']} "
                                      f"(Order ID: {orphan['order_id']})")
                    except Exception as e:
                        logger.error(f"Failed to cancel orphaned order {orphan['order_id']}: {e}")

                logger.info(f"✅ Orphaned orders cleanup completed")
            else:
                logger.info("✅ No orphaned orders found - all clean!")

        except Exception as e:
            logger.error(f"❌ Error during orphaned orders cleanup: {e}")
            logger.warning("⚠️  Continuing bot startup despite cleanup error")

    def get_market_data(self, symbol: str, interval: str = '5m', limit: int = 100) -> pd.DataFrame:
        """
        Fetch market data from Aster

        Args:
            symbol: Trading pair symbol
            interval: Candlestick interval (1m, 5m, 15m, 1h, etc.)
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data
        """

        try:
            klines = self.client.get_klines(symbol, interval, limit)

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

            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return pd.DataFrame()

    def get_funding_rate(self, symbol: str) -> Optional[List[Dict]]:
        """Get funding rate history for a symbol"""

        try:
            funding = self.client.get_funding_rate(symbol, limit=10)
            return funding
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return None

    def execute_signal(self, symbol: str, signal: Dict, strategy_name: str) -> bool:
        """
        Execute a trading signal

        Args:
            symbol: Trading pair
            signal: Signal dictionary from strategy
            strategy_name: Name of strategy generating signal

        Returns:
            True if order executed successfully
        """

        try:
            # Check if we can open position
            if not self.risk_manager.can_open_position(symbol):
                logger.warning(f"Cannot open position for {symbol}")
                return False

            # Get current price
            ticker = self.client.get_ticker_price(symbol)
            current_price = float(ticker['price'])

            # Calculate position size
            df = self.get_market_data(symbol, interval='5m', limit=50)
            if df.empty:
                logger.error(f"Cannot get market data for {symbol}")
                return False

            # Calculate ATR for position sizing
            # Use any concrete strategy for calculations (they all inherit from BaseStrategy)
            temp_strategy = self.strategies[0] if self.strategies else MarketMakingStrategy(leverage=20)
            atr = temp_strategy.calculate_atr(df).iloc[-1]
            volatility = temp_strategy.calculate_volatility(df)

            # Calculate quantity
            quantity = self.risk_manager.calculate_position_size(
                symbol,
                signal['entry_price'],
                signal['stop_loss'],
                signal['leverage'],
                volatility=volatility
            )

            # Set leverage first
            if not self.dry_run:
                try:
                    self.client.change_leverage(symbol, signal['leverage'])
                    logger.info(f"Leverage set to {signal['leverage']}x for {symbol}")
                except Exception as e:
                    logger.warning(f"Could not set leverage: {e}")
            else:
                logger.info(f"[DRY-RUN] Would set leverage to {signal['leverage']}x for {symbol}")

            # Place market order
            side = "BUY" if signal['action'] == "LONG" else "SELL"

            if not self.dry_run:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=quantity,
                    leverage=signal['leverage']
                )
                # Log full order response to verify execution
                logger.info(f"Order response: {order}")
                logger.info(f"Order executed: {side} {quantity} {symbol} @ ${current_price}")
            else:
                logger.info(f"[DRY-RUN] Would execute: {side} {quantity} {symbol} @ ${current_price}")

            # Open position in risk manager
            position = self.risk_manager.open_position(
                symbol=symbol,
                side=signal['action'],
                entry_price=current_price,
                quantity=quantity,
                leverage=signal['leverage'],
                stop_loss=signal['stop_loss'],
                take_profit=signal.get('take_profit'),
                strategy=strategy_name
            )

            if not position:
                logger.error(f"Failed to open position in risk manager")
                return False

            # Place stop loss order and save order ID
            if not self.dry_run:
                try:
                    stop_side = "SELL" if signal['action'] == "LONG" else "BUY"
                    # Round stop price to 1 decimal for BTC (price precision)
                    stop_price_rounded = round(signal['stop_loss'], 1)
                    stop_order = self.client.create_order(
                        symbol=symbol,
                        side=stop_side,
                        order_type="STOP_MARKET",
                        quantity=quantity,
                        stop_price=stop_price_rounded,
                        reduce_only=True
                    )
                    # Save SL order ID to position for later cancellation if needed
                    if 'orderId' in stop_order:
                        position.sl_order_id = str(stop_order['orderId'])
                    logger.info(f"Stop loss placed: {stop_side} @ ${stop_price_rounded} (Order ID: {position.sl_order_id})")
                except Exception as e:
                    logger.error(f"Failed to place stop loss: {e}")
            else:
                stop_side = "SELL" if signal['action'] == "LONG" else "BUY"
                logger.info(f"[DRY-RUN] Would place stop loss: {stop_side} @ ${signal['stop_loss']}")

            # Place take profit order if specified and save order ID
            if signal.get('take_profit'):
                if not self.dry_run:
                    try:
                        tp_side = "SELL" if signal['action'] == "LONG" else "BUY"
                        # Round take profit price to 1 decimal for BTC (price precision)
                        tp_price_rounded = round(signal['take_profit'], 1)
                        tp_order = self.client.create_order(
                            symbol=symbol,
                            side=tp_side,
                            order_type="TAKE_PROFIT_MARKET",
                            quantity=quantity,
                            stop_price=tp_price_rounded,
                            reduce_only=True
                        )
                        # Save TP order ID to position for later cancellation if needed
                        if 'orderId' in tp_order:
                            position.tp_order_id = str(tp_order['orderId'])
                        logger.info(f"Take profit placed: {tp_side} @ ${tp_price_rounded} (Order ID: {position.tp_order_id})")
                    except Exception as e:
                        logger.error(f"Failed to place take profit: {e}")
                else:
                    tp_side = "SELL" if signal['action'] == "LONG" else "BUY"
                    logger.info(f"[DRY-RUN] Would place take profit: {tp_side} @ ${signal['take_profit']}")

            return True

        except Exception as e:
            logger.error(f"Error executing signal for {symbol}: {e}")
            return False

    def check_positions(self):
        """Check and manage open positions, cancel orphaned orders"""

        try:
            # Get current positions from exchange
            aster_positions = self.client.get_position_info()

            # Create set of symbols with active positions on Aster
            active_on_aster = set()
            for pos in aster_positions:
                position_amt = float(pos.get('positionAmt', 0))
                if position_amt != 0:
                    active_on_aster.add(pos['symbol'])

            # Check bot's tracked positions for closed positions
            closed_positions = []
            for symbol in list(self.risk_manager.positions.keys()):
                # If position in bot but NOT on Aster → position was closed (TP or SL triggered)
                if symbol not in active_on_aster:
                    position = self.risk_manager.positions[symbol]
                    logger.warning(f"⚠️  Position {symbol} closed on exchange, canceling orphaned orders...")

                    # Try to cancel SL order if it exists
                    if position.sl_order_id:
                        try:
                            if not self.dry_run:
                                self.client.cancel_order(symbol, order_id=position.sl_order_id)
                                logger.info(f"✅ Canceled SL order {position.sl_order_id} for {symbol}")
                            else:
                                logger.info(f"[DRY-RUN] Would cancel SL order {position.sl_order_id} for {symbol}")
                        except Exception as e:
                            # Order might already be canceled or filled
                            logger.debug(f"Could not cancel SL order: {e}")

                    # Try to cancel TP order if it exists
                    if position.tp_order_id:
                        try:
                            if not self.dry_run:
                                self.client.cancel_order(symbol, order_id=position.tp_order_id)
                                logger.info(f"✅ Canceled TP order {position.tp_order_id} for {symbol}")
                            else:
                                logger.info(f"[DRY-RUN] Would cancel TP order {position.tp_order_id} for {symbol}")
                        except Exception as e:
                            # Order might already be canceled or filled
                            logger.debug(f"Could not cancel TP order: {e}")

                    # Mark for removal from tracking
                    closed_positions.append(symbol)

            # Clean up closed positions from bot tracking
            for symbol in closed_positions:
                position = self.risk_manager.positions[symbol]
                # Get final PnL from exchange before removing
                try:
                    # Fetch recent trades to get exit price AND realized PnL
                    account_trades = self.client._request("GET", "/fapi/v3/userTrades", signed=True, params={"symbol": symbol, "limit": 10})
                    if account_trades:
                        # Find the closing trade (most recent)
                        exit_price = float(account_trades[0].get('price', position.entry_price))

                        # Sum up all realized PnL from trades (in case of partial fills)
                        total_realized_pnl = sum(float(trade.get('realizedPnl', 0)) for trade in account_trades)

                        logger.info(f"📊 Position {symbol} exit price: ${exit_price:.2f}, Realized PnL from Aster: ${total_realized_pnl:.2f}")

                        # Close position in risk manager using REAL PnL from Aster
                        self.risk_manager.close_position(
                            symbol,
                            exit_price,
                            strategy=position.strategy,
                            realized_pnl=total_realized_pnl  # Use real PnL from exchange
                        )
                        logger.info(f"✅ Position {symbol} closed and recorded with real PnL from exchange")
                    else:
                        # If we can't get trade data, just remove from tracking
                        del self.risk_manager.positions[symbol]
                        logger.info(f"🗑️  Position {symbol} removed from tracking (no trade history found)")
                except Exception as e:
                    logger.debug(f"Could not fetch trade data for {symbol}: {e}")
                    # Just remove from tracking if we can't get trade data
                    if symbol in self.risk_manager.positions:
                        del self.risk_manager.positions[symbol]
                        logger.info(f"🗑️  Position {symbol} removed from tracking (error fetching data)")

            # Update remaining active positions with current prices
            for pos in aster_positions:
                symbol = pos['symbol']
                position_amt = float(pos.get('positionAmt', 0))

                # Skip if no position
                if position_amt == 0:
                    continue

                current_price = float(pos['markPrice'])

                # Update position in risk manager
                if symbol in self.risk_manager.positions:
                    self.risk_manager.update_position(symbol, current_price)

                    # Check stop loss and take profit (for logging purposes)
                    if self.risk_manager.check_stop_loss(symbol, current_price):
                        logger.warning(f"⚠️  Stop loss threshold reached for {symbol}")

                    elif self.risk_manager.check_take_profit(symbol, current_price):
                        logger.info(f"🎯 Take profit threshold reached for {symbol}")

        except Exception as e:
            logger.error(f"Error checking positions: {e}")

    def get_orderbook(self, symbol: str) -> Optional[Dict]:
        """Get order book for a symbol"""
        try:
            orderbook = self.client.get_order_book(symbol, limit=10)
            return orderbook
        except Exception as e:
            logger.debug(f"Could not fetch orderbook for {symbol}: {e}")
            return None

    def analyze_markets(self):
        """Analyze all markets and generate signals"""

        # Update market regime even if we have positions
        if self.use_dynamic_selector and self.strategy_selector:
            try:
                # Get data for primary symbol to update regime
                primary_symbol = self.symbols[0] if self.symbols else "BTCUSDT"
                df = self.get_market_data(primary_symbol, interval='5m', limit=100)

                if not df.empty:
                    # Get additional data for regime detection
                    funding_history = self.get_funding_rate(primary_symbol)
                    orderbook = self.get_orderbook(primary_symbol)

                    # Update regime using the proper method that calculates all required indicators
                    regime, confidence = self.strategy_selector.regime_detector.update_regime(
                        df, orderbook, funding_history, timestamp=None
                    )
                    self.current_regime = regime
                    logger.debug(f"Market Regime updated: {regime.value} (confidence: {confidence:.2%})")

                    # Select best strategy for current regime (even if we don't trade)
                    # This ensures dashboard always shows which strategy is recommended
                    timestamp = int(datetime.now().timestamp())
                    result = self.strategy_selector.select_strategy(df, orderbook, funding_history, timestamp)
                    if result:
                        strategy_name, score = result
                        self.selected_strategy_name = strategy_name
                        logger.debug(f"Selected strategy for regime: {strategy_name} (score: {score:.2f})")

            except Exception as e:
                logger.debug(f"Error updating market regime: {e}")

        for symbol in self.symbols:
            try:
                # Skip if already in position
                if symbol in self.risk_manager.positions:
                    continue

                # Get market data
                df = self.get_market_data(symbol, interval='5m', limit=100)

                if df.empty:
                    continue

                # Get additional data for dynamic selector
                funding_history = self.get_funding_rate(symbol)
                orderbook = self.get_orderbook(symbol) if self.use_dynamic_selector else None

                # Use dynamic selector if enabled
                if self.use_dynamic_selector and self.strategy_selector:
                    try:
                        # Get timestamp
                        timestamp = int(datetime.now().timestamp())

                        # Analyze with best strategy
                        signal = self.strategy_selector.analyze_with_best_strategy(
                            df, symbol, orderbook, funding_history, timestamp
                        )

                        if signal:
                            strategy_name = signal.get('selected_strategy', 'Unknown')
                            self.current_regime = self.strategy_selector.regime_detector.current_regime
                            self.selected_strategy_name = strategy_name

                            logger.info(f"🎯 Signal from Dynamic Selector: {strategy_name} → {signal['action']} for {symbol}")
                            logger.info(f"   Market Regime: {signal.get('market_regime', 'unknown')}")

                            # Execute signal
                            success = self.execute_signal(symbol, signal, strategy_name)

                            if success:
                                logger.info(f"✅ Signal executed successfully for {symbol}")

                    except Exception as e:
                        logger.error(f"Error with dynamic selector for {symbol}: {e}")

                else:
                    # Static strategy selection (original logic)
                    for strategy in self.strategies:
                        try:
                            # Generate signal
                            if strategy.name == "Funding Arbitrage" and funding_history:
                                signal = strategy.analyze(df, symbol, funding_history=funding_history)
                            else:
                                signal = strategy.analyze(df, symbol)

                            if signal:
                                logger.info(f"Signal generated by {strategy.name} for {symbol}: {signal['action']}")

                                # Execute signal
                                success = self.execute_signal(symbol, signal, strategy.name)

                                if success:
                                    logger.info(f"Signal executed successfully for {symbol}")
                                    break  # Only one strategy per symbol

                        except Exception as e:
                            logger.error(f"Error analyzing with {strategy.name} for {symbol}: {e}")

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")

    def run_iteration(self):
        """Run one iteration of the bot"""

        logger.info("Running bot iteration...")

        # Reset daily stats if needed
        self.risk_manager.reset_daily_stats()

        # Check existing positions
        self.check_positions()

        # Analyze markets for new opportunities
        self.analyze_markets()

        # Log current status
        stats = self.risk_manager.get_statistics()
        logger.info(f"Status: Capital=${stats['current_capital']:.2f}, "
                   f"Open Positions={stats['open_positions']}, "
                   f"Daily PnL=${stats['daily_pnl']:.2f}")

    def start(self, interval_seconds: int = 60):
        """
        Start the trading bot

        Args:
            interval_seconds: Seconds between iterations
        """

        logger.info("Starting trading bot...")
        self.is_running = True

        try:
            while self.is_running:
                try:
                    self.run_iteration()
                except Exception as e:
                    logger.error(f"Error in bot iteration: {e}")

                # Wait for next iteration
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            self.stop()

    def stop(self):
        """Stop the trading bot"""

        logger.info("Stopping trading bot...")
        self.is_running = False

        # Print final statistics
        stats = self.risk_manager.get_statistics()

        logger.info("\n" + "="*50)
        logger.info("FINAL STATISTICS")
        logger.info("="*50)
        logger.info(f"Total Trades: {stats['total_trades']}")
        logger.info(f"Winning Trades: {stats['winning_trades']}")
        logger.info(f"Losing Trades: {stats['losing_trades']}")
        logger.info(f"Win Rate: {stats['win_rate']:.2f}%")
        logger.info(f"Total PnL: ${stats['total_pnl']:.2f}")
        logger.info(f"ROI: {stats['roi']:.2f}%")
        logger.info(f"Final Capital: ${stats['current_capital']:.2f}")
        logger.info("="*50)
