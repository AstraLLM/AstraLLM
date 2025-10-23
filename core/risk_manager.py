"""
Risk Management System for High Leverage Trading
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
from core.bot_state import BotStateManager


@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    quantity: float
    leverage: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    liquidation_price: Optional[float] = None
    entry_time: datetime = None
    strategy: str = "unknown"
    # Order IDs for SL/TP to enable cancellation
    sl_order_id: Optional[str] = None
    tp_order_id: Optional[str] = None

    def __post_init__(self):
        if self.entry_time is None:
            self.entry_time = datetime.now()


@dataclass
class Trade:
    """Represents a completed trade"""
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    leverage: int
    pnl: float
    pnl_percentage: float
    entry_time: datetime
    exit_time: datetime
    strategy: str


class RiskManager:
    """
    Advanced Risk Management for High Leverage Trading

    Features:
    - Dynamic position sizing based on volatility
    - Multi-level stop loss system
    - Liquidation protection
    - Daily/weekly loss limits
    - Correlation-based exposure management
    """

    def __init__(self,
                 initial_capital: float,
                 max_leverage: int = 50,
                 risk_per_trade: float = 0.02,
                 max_daily_loss: float = 0.10,
                 max_open_positions: int = 5,
                 min_risk_reward: float = 1.5,
                 db_path: str = "data/bot_state.db"):

        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_leverage = max_leverage
        self.risk_per_trade = risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_open_positions = max_open_positions
        self.min_risk_reward = min_risk_reward

        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset = datetime.now()

        # Initialize database manager for trade logging
        self.db_manager = BotStateManager(db_path)

        logger.info(f"RiskManager initialized: Capital=${initial_capital}, Max Leverage={max_leverage}x")

    def reset_daily_stats(self):
        """Reset daily statistics"""
        if datetime.now() - self.last_reset > timedelta(days=1):
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset = datetime.now()
            logger.info("Daily stats reset")

    def can_open_position(self, symbol: str) -> bool:
        """Check if we can open a new position"""
        self.reset_daily_stats()

        # Check daily loss limit
        if self.daily_pnl < -(self.initial_capital * self.max_daily_loss):
            logger.warning(f"Daily loss limit reached: ${self.daily_pnl:.2f}")
            return False

        # Check max positions
        if len(self.positions) >= self.max_open_positions:
            logger.warning(f"Max positions limit reached: {len(self.positions)}")
            return False

        # Check if already in position for this symbol
        if symbol in self.positions:
            logger.warning(f"Already in position for {symbol}")
            return False

        # Check if capital is sufficient
        if self.current_capital <= self.initial_capital * 0.5:
            logger.warning(f"Capital too low: ${self.current_capital:.2f}")
            return False

        return True

    def calculate_position_size(self,
                                 symbol: str,
                                 entry_price: float,
                                 stop_loss: float,
                                 leverage: int,
                                 volatility: Optional[float] = None) -> float:
        """
        Calculate optimal position size based on risk parameters

        Uses:
        - Fixed risk per trade (% of capital)
        - ATR-based volatility adjustment
        - Dynamic leverage scaling
        """

        # Calculate risk amount
        risk_amount = self.current_capital * self.risk_per_trade

        # Adjust for volatility if provided
        if volatility:
            # Reduce size in high volatility
            volatility_multiplier = max(0.5, 1 - (volatility * 2))
            risk_amount *= volatility_multiplier

        # Calculate stop loss distance in percentage
        stop_distance = abs(entry_price - stop_loss) / entry_price

        # Position size = Risk Amount / (Stop Distance * Entry Price)
        # With leverage, effective position size multiplies
        position_value = risk_amount / stop_distance
        quantity = position_value / entry_price

        # Adjust for leverage (reduce quantity as leverage increases for safety)
        leverage_adjustment = min(1.0, 20 / leverage)
        quantity *= leverage_adjustment

        logger.info(f"Position size calculated: {quantity:.4f} {symbol} @ ${entry_price} (Leverage: {leverage}x)")

        return quantity

    def calculate_stop_loss(self,
                             entry_price: float,
                             side: str,
                             atr: float,
                             leverage: int,
                             tight: bool = False) -> float:
        """
        Calculate optimal stop loss based on ATR and leverage

        For high leverage:
        - Use tighter stops (1-2% from entry)
        - Scale with ATR
        - Adjust for leverage risk
        """

        # Base stop distance as multiple of ATR
        if tight:
            atr_multiplier = 1.0  # Tight stop for scalping
        else:
            atr_multiplier = 1.5  # Normal stop

        stop_distance = atr * atr_multiplier

        # Adjust for leverage - higher leverage needs tighter stops
        leverage_factor = max(0.5, 1 - (leverage - 10) / 100)
        stop_distance *= leverage_factor

        # Calculate stop price
        if side == "LONG":
            stop_price = entry_price - stop_distance
        else:  # SHORT
            stop_price = entry_price + stop_distance

        # Ensure stop doesn't exceed max risk per trade
        max_stop_distance = entry_price * (self.risk_per_trade / leverage * 5)
        if abs(entry_price - stop_price) > max_stop_distance:
            if side == "LONG":
                stop_price = entry_price - max_stop_distance
            else:
                stop_price = entry_price + max_stop_distance

        return stop_price

    def calculate_take_profit(self,
                               entry_price: float,
                               stop_loss: float,
                               side: str,
                               risk_reward_ratio: float = 2.0) -> float:
        """Calculate take profit based on risk/reward ratio"""

        stop_distance = abs(entry_price - stop_loss)
        profit_distance = stop_distance * risk_reward_ratio

        if side == "LONG":
            take_profit = entry_price + profit_distance
        else:  # SHORT
            take_profit = entry_price - profit_distance

        return take_profit

    def calculate_liquidation_price(self,
                                      entry_price: float,
                                      leverage: int,
                                      side: str,
                                      maintenance_margin_rate: float = 0.005) -> float:
        """
        Calculate liquidation price

        Liquidation occurs when:
        Loss = (Entry Price / Leverage) - Maintenance Margin
        """

        if side == "LONG":
            # Long liquidation: Price drops
            liquidation_price = entry_price * (1 - (1/leverage) + maintenance_margin_rate)
        else:  # SHORT
            # Short liquidation: Price rises
            liquidation_price = entry_price * (1 + (1/leverage) - maintenance_margin_rate)

        return liquidation_price

    def open_position(self,
                       symbol: str,
                       side: str,
                       entry_price: float,
                       quantity: float,
                       leverage: int,
                       stop_loss: float,
                       take_profit: Optional[float] = None,
                       strategy: str = "unknown") -> Optional[Position]:
        """Open a new position"""

        if not self.can_open_position(symbol):
            return None

        # Calculate liquidation price
        liquidation_price = self.calculate_liquidation_price(entry_price, leverage, side)

        # Safety check: ensure stop loss is before liquidation
        if side == "LONG":
            if stop_loss <= liquidation_price:
                logger.error(f"Stop loss too close to liquidation! Stop: {stop_loss}, Liq: {liquidation_price}")
                return None
        else:
            if stop_loss >= liquidation_price:
                logger.error(f"Stop loss too close to liquidation! Stop: {stop_loss}, Liq: {liquidation_price}")
                return None

        position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
            liquidation_price=liquidation_price,
            strategy=strategy
        )

        self.positions[symbol] = position
        self.daily_trades += 1

        tp_str = f"${take_profit:.2f}" if take_profit else "None"
        logger.info(f"Position opened: {side} {quantity} {symbol} @ ${entry_price} "
                   f"[SL: ${stop_loss:.2f}, TP: {tp_str}, "
                   f"Liq: ${liquidation_price:.2f}] {leverage}x leverage")

        return position

    def close_position(self,
                        symbol: str,
                        exit_price: float,
                        strategy: str = "unknown",
                        realized_pnl: Optional[float] = None) -> Optional[Trade]:
        """
        Close an existing position

        Args:
            symbol: Trading pair symbol
            exit_price: Exit price
            strategy: Strategy name
            realized_pnl: If provided, use this PnL directly from exchange instead of calculating
        """

        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return None

        position = self.positions[symbol]

        # Use realized PnL from exchange if provided, otherwise calculate
        if realized_pnl is not None:
            # Use real PnL from exchange (most accurate)
            pnl = realized_pnl
            pnl_percentage = (pnl / (position.entry_price * position.quantity)) * 100
            logger.debug(f"Using realized PnL from exchange: ${pnl:.2f}")
        else:
            # Calculate PnL manually (fallback)
            if position.side == "LONG":
                pnl_per_unit = exit_price - position.entry_price
            else:  # SHORT
                pnl_per_unit = position.entry_price - exit_price

            # CORRECTED: Don't multiply by leverage for PnL calculation
            pnl = pnl_per_unit * position.quantity
            pnl_percentage = (pnl_per_unit / position.entry_price) * 100
            logger.debug(f"Calculated PnL manually: ${pnl:.2f}")

        # Update capital and stats
        self.current_capital += pnl
        self.daily_pnl += pnl

        # Create trade record
        trade = Trade(
            symbol=symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            leverage=position.leverage,
            pnl=pnl,
            pnl_percentage=pnl_percentage,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            strategy=strategy
        )

        self.trades.append(trade)
        del self.positions[symbol]

        logger.info(f"Position closed: {symbol} @ ${exit_price} | "
                   f"PnL: ${pnl:.2f} ({pnl_percentage:.2f}%) | "
                   f"Capital: ${self.current_capital:.2f}")

        # ===== SAVE TRADE TO DATABASE =====
        try:
            trade_data = {
                'symbol': trade.symbol,
                'strategy': trade.strategy,
                'side': trade.side,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'quantity': trade.quantity,
                'leverage': trade.leverage,
                'pnl': trade.pnl,
                'pnl_percentage': trade.pnl_percentage,
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'stop_loss': position.stop_loss,
                'take_profit': position.take_profit,
                'exit_reason': strategy,  # Could be enhanced with more specific reasons
                'confidence': getattr(position, 'confidence', None)
            }

            self.db_manager.save_trade(trade_data)

            # Update strategy performance stats
            hold_time = (trade.exit_time - trade.entry_time).total_seconds()
            is_winner = trade.pnl > 0
            self.db_manager.update_strategy_performance(
                strategy=trade.strategy,
                trade_pnl=trade.pnl,
                hold_time_seconds=int(hold_time),
                is_winner=is_winner
            )

        except Exception as e:
            logger.error(f"Failed to save trade to database: {e}")
            # Don't fail the trade closure if DB save fails

        return trade

    def update_position(self, symbol: str, current_price: float):
        """Update position with current market price"""

        if symbol not in self.positions:
            return

        position = self.positions[symbol]

        # Calculate unrealized PnL
        if position.side == "LONG":
            pnl_per_unit = current_price - position.entry_price
        else:
            pnl_per_unit = position.entry_price - current_price

        # FIXED: Don't multiply by leverage! Leverage affects margin, not PnL
        position.unrealized_pnl = pnl_per_unit * position.quantity

    def check_stop_loss(self, symbol: str, current_price: float) -> bool:
        """Check if stop loss is hit"""

        if symbol not in self.positions:
            return False

        position = self.positions[symbol]

        if position.stop_loss is None:
            return False

        if position.side == "LONG":
            if current_price <= position.stop_loss:
                logger.warning(f"Stop loss hit for {symbol}: ${current_price} <= ${position.stop_loss}")
                return True
        else:  # SHORT
            if current_price >= position.stop_loss:
                logger.warning(f"Stop loss hit for {symbol}: ${current_price} >= ${position.stop_loss}")
                return True

        return False

    def check_take_profit(self, symbol: str, current_price: float) -> bool:
        """Check if take profit is hit"""

        if symbol not in self.positions:
            return False

        position = self.positions[symbol]

        if position.take_profit is None:
            return False

        if position.side == "LONG":
            if current_price >= position.take_profit:
                logger.info(f"Take profit hit for {symbol}: ${current_price} >= ${position.take_profit}")
                return True
        else:  # SHORT
            if current_price <= position.take_profit:
                logger.info(f"Take profit hit for {symbol}: ${current_price} <= ${position.take_profit}")
                return True

        return False

    def get_statistics(self) -> Dict:
        """Get trading statistics"""

        if not self.trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "current_capital": self.current_capital,
                "roi": 0.0,
                "daily_pnl": self.daily_pnl,
                "open_positions": len(self.positions)
            }

        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]

        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))

        avg_win = total_wins / len(winning_trades) if winning_trades else 0
        avg_loss = total_losses / len(losing_trades) if losing_trades else 0

        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Calculate max drawdown
        capital_curve = [self.initial_capital]
        for trade in self.trades:
            capital_curve.append(capital_curve[-1] + trade.pnl)

        peak = capital_curve[0]
        max_dd = 0
        for capital in capital_curve:
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak
            if dd > max_dd:
                max_dd = dd

        return {
            "total_trades": len(self.trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(self.trades) * 100,
            "total_pnl": sum(t.pnl for t in self.trades),
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "max_drawdown": max_dd * 100,
            "current_capital": self.current_capital,
            "roi": (self.current_capital - self.initial_capital) / self.initial_capital * 100,
            "daily_pnl": self.daily_pnl,
            "open_positions": len(self.positions)
        }
