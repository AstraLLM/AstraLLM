"""
Liquidation Cascade Strategy

Optimized for high leverage (40-50x)
Best for: High volatility, capitulating markets

Strategy:
- Detect liquidation zones using volume and price action
- Enter when cascading liquidations are likely
- Ride the momentum from forced selling/buying
- Very aggressive - requires precise timing
"""
from typing import Dict, Optional
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from loguru import logger


class LiquidationCascadeStrategy(BaseStrategy):
    """
    Liquidation Cascade Trading

    Entry Conditions:
    1. Sharp price move (5%+ in short time)
    2. Massive volume spike (3x+ average)
    3. Signs of forced liquidations
    4. Momentum continuation expected

    This is the most aggressive strategy - use with caution!

    Exit:
    - Stop Loss: 1.2% from entry (very tight)
    - Take Profit: 4% from entry (high R/R needed)
    """

    def __init__(self, leverage: int = 45):
        super().__init__("Liquidation Cascade", leverage)
        self.sharp_move_threshold = 0.05  # 5% move
        self.volume_spike = 3.0  # 3x volume
        self.lookback_candles = 10
        self.stop_loss_pct = 0.012  # 1.2%
        self.take_profit_pct = 0.040  # 4.0%

    def get_required_candles(self) -> int:
        return 50

    def detect_liquidation_event(self, df: pd.DataFrame) -> Optional[str]:
        """
        Detect potential liquidation cascade

        Returns:
            'LONG_LIQ' - Long positions being liquidated (price dropping)
            'SHORT_LIQ' - Short positions being liquidated (price rising)
            None - No liquidation detected
        """
        if len(df) < self.lookback_candles + 1:
            return None

        # Calculate price change over lookback period
        recent_prices = df['close'].iloc[-(self.lookback_candles+1):]
        price_change = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]

        # Check for sharp move
        if abs(price_change) < self.sharp_move_threshold:
            return None

        # Check volume spike
        volume_ratio = self.calculate_volume_profile(df, self.lookback_candles)

        if volume_ratio < self.volume_spike:
            return None

        # Determine direction
        if price_change > self.sharp_move_threshold:
            # Sharp move up - shorts being liquidated
            return 'SHORT_LIQ'
        elif price_change < -self.sharp_move_threshold:
            # Sharp move down - longs being liquidated
            return 'LONG_LIQ'

        return None

    def calculate_momentum_strength(self, df: pd.DataFrame) -> float:
        """
        Calculate momentum strength

        Returns:
            Value 0-1 indicating momentum strength
        """
        if len(df) < 20:
            return 0.0

        # Use rate of change and volume
        roc = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
        volume_ratio = self.calculate_volume_profile(df, 10)

        momentum = abs(roc) * min(volume_ratio / 3.0, 1.0)

        return min(momentum * 5, 1.0)  # Scale to 0-1

    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """Analyze for liquidation cascade opportunities"""

        if len(df) < self.get_required_candles():
            return None

        # Detect liquidation event
        liq_event = self.detect_liquidation_event(df)

        if liq_event is None:
            return None

        # Calculate indicators
        rsi = self.calculate_rsi(df, period=14)
        current_rsi = rsi.iloc[-1]
        current_price = df['close'].iloc[-1]

        # Calculate momentum strength
        momentum = self.calculate_momentum_strength(df)

        signal = None

        if liq_event == 'SHORT_LIQ':
            # Shorts being liquidated - price going UP
            # Enter LONG to ride the cascade

            # Don't enter if already extremely overbought
            if current_rsi > 80:
                logger.debug(f"RSI too high for long entry: {current_rsi}")
                return None

            entry_price = current_price
            stop_loss = entry_price * (1 - self.stop_loss_pct)
            take_profit = entry_price * (1 + self.take_profit_pct)

            confidence = min(0.85, momentum)

            signal = {
                'action': 'LONG',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': self.default_leverage,
                'confidence': confidence,
                'reason': f'Short Liquidation Cascade: RSI={current_rsi:.1f}, Momentum={momentum:.2f}'
            }

        elif liq_event == 'LONG_LIQ':
            # Longs being liquidated - price going DOWN
            # Enter SHORT to ride the cascade

            # Don't enter if already extremely oversold
            if current_rsi < 20:
                logger.debug(f"RSI too low for short entry: {current_rsi}")
                return None

            entry_price = current_price
            stop_loss = entry_price * (1 + self.stop_loss_pct)
            take_profit = entry_price * (1 - self.take_profit_pct)

            confidence = min(0.85, momentum)

            signal = {
                'action': 'SHORT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': self.default_leverage,
                'confidence': confidence,
                'reason': f'Long Liquidation Cascade: RSI={current_rsi:.1f}, Momentum={momentum:.2f}'
            }

        if signal and self.validate_signal(signal):
            logger.info(f"[{self.name}] Signal generated for {symbol}: {signal['action']} @ ${signal['entry_price']:.4f}")
            return signal

        return None
