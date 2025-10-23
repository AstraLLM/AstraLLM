"""
Base Strategy Class
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from loguru import logger


class BaseStrategy(ABC):
    """Abstract base class for trading strategies"""

    def __init__(self, name: str, default_leverage: int = 20):
        self.name = name
        self.default_leverage = default_leverage
        self.signals: List[Dict] = []
        logger.info(f"Strategy initialized: {name} (Leverage: {default_leverage}x)")

    @abstractmethod
    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """
        Analyze market data and generate trading signal

        Returns:
            Dict with keys: {
                'action': 'LONG' or 'SHORT',
                'entry_price': float,
                'stop_loss': float,
                'take_profit': float,
                'leverage': int,
                'confidence': float (0-1),
                'reason': str
            }
        """
        pass

    @abstractmethod
    def get_required_candles(self) -> int:
        """Return minimum number of candles required for analysis"""
        pass

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        close = df['close']
        delta = close.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return df['close'].ewm(span=period, adjust=False).mean()

    def calculate_sma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return df['close'].rolling(window=period).mean()

    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = self.calculate_sma(df, period)
        rolling_std = df['close'].rolling(window=period).std()

        upper_band = sma + (rolling_std * std)
        lower_band = sma - (rolling_std * std)

        return upper_band, sma, lower_band

    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD"""
        ema_fast = self.calculate_ema(df, fast)
        ema_slow = self.calculate_ema(df, slow)

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def calculate_volume_profile(self, df: pd.DataFrame, period: int = 20) -> float:
        """Calculate volume profile - current volume vs average"""
        if len(df) < period:
            return 1.0

        avg_volume = df['volume'].rolling(window=period).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]

        if avg_volume == 0:
            return 1.0

        return current_volume / avg_volume

    def detect_breakout(self, df: pd.DataFrame, period: int = 20) -> Optional[str]:
        """
        Detect price breakout from recent range

        Returns:
            'UP' for upward breakout
            'DOWN' for downward breakout
            None for no breakout
        """
        if len(df) < period + 1:
            return None

        recent_high = df['high'].iloc[-(period+1):-1].max()
        recent_low = df['low'].iloc[-(period+1):-1].min()
        current_close = df['close'].iloc[-1]

        # Breakout threshold (1% above/below range)
        threshold = 0.01

        if current_close > recent_high * (1 + threshold):
            return 'UP'
        elif current_close < recent_low * (1 - threshold):
            return 'DOWN'

        return None

    def calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """Calculate recent price volatility (standard deviation)"""
        if len(df) < period:
            return 0.0

        returns = df['close'].pct_change()
        volatility = returns.rolling(window=period).std().iloc[-1]

        return volatility if not pd.isna(volatility) else 0.0

    def is_trending(self, df: pd.DataFrame, period: int = 50) -> Tuple[bool, Optional[str]]:
        """
        Determine if market is trending

        Returns:
            (is_trending, direction)
            direction: 'UP', 'DOWN', or None
        """
        if len(df) < period:
            return False, None

        ema_short = self.calculate_ema(df, period // 2)
        ema_long = self.calculate_ema(df, period)

        if ema_short.iloc[-1] > ema_long.iloc[-1] * 1.02:
            return True, 'UP'
        elif ema_short.iloc[-1] < ema_long.iloc[-1] * 0.98:
            return True, 'DOWN'

        return False, None

    def validate_signal(self, signal: Dict) -> bool:
        """Validate signal structure"""
        required_keys = ['action', 'entry_price', 'stop_loss', 'leverage', 'confidence', 'reason']

        for key in required_keys:
            if key not in signal:
                logger.error(f"Missing required key in signal: {key}")
                return False

        if signal['action'] not in ['LONG', 'SHORT']:
            logger.error(f"Invalid action: {signal['action']}")
            return False

        if signal['leverage'] <= 0 or signal['leverage'] > 100:
            logger.error(f"Invalid leverage: {signal['leverage']}")
            return False

        if signal['confidence'] < 0 or signal['confidence'] > 1:
            logger.error(f"Invalid confidence: {signal['confidence']}")
            return False

        return True
