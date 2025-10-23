"""
Funding Rate Arbitrage Strategy

Optimized for high leverage (10-30x)
Best for: Exploiting funding rate inefficiencies

Strategy:
- Monitor funding rates across perpetual contracts
- Enter positions when funding rates are extreme
- Hold through funding payment
- Low directional risk, captures funding payments
"""
from typing import Dict, Optional, List
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from loguru import logger


class FundingArbitrageStrategy(BaseStrategy):
    """
    Funding Rate Arbitrage

    Entry Conditions:
    1. Funding rate > 0.1% (or < -0.1%)
    2. Trend confirmation in funding direction
    3. Low volatility environment (safer for this strategy)

    Strategy:
    - If funding positive (longs pay shorts): SHORT
    - If funding negative (shorts pay longs): LONG
    - Hold for funding payment + small directional profit

    Exit:
    - After funding payment received
    - Stop loss: 2% (wider than scalping strategies)
    - Take profit: 1.5% + funding payment
    """

    def __init__(self, leverage: int = 20):
        super().__init__("Funding Arbitrage", leverage)
        self.funding_threshold = 0.001  # 0.1%
        self.stop_loss_pct = 0.020  # 2.0%
        self.take_profit_pct = 0.015  # 1.5%
        self.max_volatility = 0.03  # 3% max volatility

    def get_required_candles(self) -> int:
        return 30

    def analyze_funding_rate(self, funding_history: List[Dict]) -> Optional[float]:
        """
        Analyze funding rate history

        Returns:
            Current funding rate or None
        """
        if not funding_history:
            return None

        # Get most recent funding rate
        latest = funding_history[-1]
        return float(latest.get('fundingRate', 0))

    def analyze(self, df: pd.DataFrame, symbol: str,
                funding_history: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Analyze for funding arbitrage opportunities"""

        if len(df) < self.get_required_candles():
            return None

        # Check if funding data is available
        if not funding_history:
            logger.debug(f"No funding history for {symbol}")
            return None

        # Calculate volatility
        volatility = self.calculate_volatility(df)

        # Only trade in low volatility (safer for funding arb)
        if volatility > self.max_volatility:
            logger.debug(f"Volatility too high for funding arb: {volatility:.4f}")
            return None

        # Get funding rate
        current_funding = self.analyze_funding_rate(funding_history)

        if current_funding is None:
            return None

        current_price = df['close'].iloc[-1]
        signal = None

        # High positive funding - longs are paying shorts
        if current_funding > self.funding_threshold:
            # Enter SHORT to collect funding
            entry_price = current_price
            stop_loss = entry_price * (1 + self.stop_loss_pct)
            take_profit = entry_price * (1 - self.take_profit_pct)

            # Confidence based on funding rate magnitude
            confidence = min(0.9, abs(current_funding) / 0.003)

            signal = {
                'action': 'SHORT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': self.default_leverage,
                'confidence': confidence,
                'reason': f'High Funding: {current_funding*100:.3f}% (Shorts earn), Vol={volatility*100:.2f}%'
            }

        # High negative funding - shorts are paying longs
        elif current_funding < -self.funding_threshold:
            # Enter LONG to collect funding
            entry_price = current_price
            stop_loss = entry_price * (1 - self.stop_loss_pct)
            take_profit = entry_price * (1 + self.take_profit_pct)

            # Confidence based on funding rate magnitude
            confidence = min(0.9, abs(current_funding) / 0.003)

            signal = {
                'action': 'LONG',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': self.default_leverage,
                'confidence': confidence,
                'reason': f'Low Funding: {current_funding*100:.3f}% (Longs earn), Vol={volatility*100:.2f}%'
            }

        if signal and self.validate_signal(signal):
            logger.info(f"[{self.name}] Signal generated for {symbol}: {signal['action']} @ ${signal['entry_price']:.4f}")
            return signal

        return None
