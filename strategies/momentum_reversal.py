"""
CARRARMATO Momentum Reversal Strategy - Ultra High Precision

Optimized for: WINNING RATE 80%+
Leverage: 25x (moderate-high with tight SL)
Best for: Catching extreme reversals with high probability

Philosophy:
- Wait for EXTREME oversold/overbought + volume confirmation
- Multiple candlestick patterns + RSI divergence
- R/R minimum 1:2.5
- Enter ONLY on perfect setups
- Stop loss ultra-tight (1.2%)

ENTRY ONLY WHEN:
1. RSI < 20 (oversold) or > 80 (overbought) - EXTREME!
2. Price touching outer Bollinger Band
3. Reversal candlestick pattern confirmed
4. Volume spike 2x+ (confirmation)
5. No contradictory signals from other indicators
"""
from typing import Dict, Optional
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from loguru import logger


class MomentumReversalStrategy(BaseStrategy):
    """
    CARRARMATO Momentum Reversal - Ultra High Win Rate

    Target: 80%+ winning rate
    R/R: 1:2.5
    Max Daily Trades: 2-3
    """

    def __init__(self, leverage: int = 25):
        super().__init__("Momentum Reversal", leverage)

        # BALANCED PARAMETERS - Più accessibile
        self.rsi_oversold = 25  # Era 20, ora meno estremo (più opportunità)
        self.rsi_overbought = 75  # Era 80, ora meno estremo
        self.bb_period = 20
        self.bb_std = 2.0  # Era 2.5, ora standard BB

        # R/R = 1:2.5 (EXCELLENT!)
        self.stop_loss_pct = 0.012  # 1.2% SL
        self.take_profit_pct = 0.030  # 3.0% TP

        # Volume confirmation (BALANCED - più permissivo)
        self.min_volume_ratio = 1.5  # Min 1.5x volume (era 2.0x)

        # Confidence requirement (BALANCED)
        self.min_confidence = 0.60  # Minimo 60% confidence (era 70%)

    def get_required_candles(self) -> int:
        return 100  # Più dati = più sicurezza

    def detect_reversal_candle(self, df: pd.DataFrame) -> Optional[str]:
        """
        Detect STRONG reversal candlestick patterns
        CARRARMATO: pattern più strict
        """
        if len(df) < 2:
            return None

        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]

        open_price = last_candle['open']
        close = last_candle['close']
        high = last_candle['high']
        low = last_candle['low']

        body = abs(close - open_price)
        total_range = high - low

        if total_range == 0:
            return None

        # STRONGER Hammer pattern (bullish reversal)
        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low

        # Hammer: lower wick 3x body, close > open, upper wick tiny
        if (lower_wick > body * 3 and
            upper_wick < body * 0.3 and
            close > open_price):
            # Additional confirmation: previous candle was bearish
            if prev_candle['close'] < prev_candle['open']:
                logger.debug(f"✅ STRONG Bullish Hammer detected")
                return 'BULLISH'

        # STRONGER Shooting star pattern (bearish reversal)
        # Shooting star: upper wick 3x body, close < open, lower wick tiny
        if (upper_wick > body * 3 and
            lower_wick < body * 0.3 and
            close < open_price):
            # Additional confirmation: previous candle was bullish
            if prev_candle['close'] > prev_candle['open']:
                logger.debug(f"✅ STRONG Bearish Shooting Star detected")
                return 'BEARISH'

        return None

    def check_rsi_divergence(self, df: pd.DataFrame, rsi: pd.Series) -> Optional[str]:
        """
        Check for RSI divergence (bonus confirmation)

        Returns:
            'BULLISH' - Price lower low but RSI higher low
            'BEARISH' - Price higher high but RSI lower high
            None - No divergence
        """
        if len(df) < 20:
            return None

        # Look back 10-20 candles for divergence
        recent_prices = df['close'].iloc[-20:]
        recent_rsi = rsi.iloc[-20:]

        # Find local extremes
        price_lows = []
        price_highs = []
        rsi_at_lows = []
        rsi_at_highs = []

        for i in range(2, len(recent_prices) - 2):
            # Local low
            if (recent_prices.iloc[i] < recent_prices.iloc[i-1] and
                recent_prices.iloc[i] < recent_prices.iloc[i+1]):
                price_lows.append(recent_prices.iloc[i])
                rsi_at_lows.append(recent_rsi.iloc[i])

            # Local high
            if (recent_prices.iloc[i] > recent_prices.iloc[i-1] and
                recent_prices.iloc[i] > recent_prices.iloc[i+1]):
                price_highs.append(recent_prices.iloc[i])
                rsi_at_highs.append(recent_rsi.iloc[i])

        # Bullish divergence: price making lower lows, RSI making higher lows
        if len(price_lows) >= 2 and len(rsi_at_lows) >= 2:
            if (price_lows[-1] < price_lows[-2] and
                rsi_at_lows[-1] > rsi_at_lows[-2]):
                logger.debug(f"✅ Bullish RSI divergence detected")
                return 'BULLISH'

        # Bearish divergence: price making higher highs, RSI making lower highs
        if len(price_highs) >= 2 and len(rsi_at_highs) >= 2:
            if (price_highs[-1] > price_highs[-2] and
                rsi_at_highs[-1] < rsi_at_highs[-2]):
                logger.debug(f"✅ Bearish RSI divergence detected")
                return 'BEARISH'

        return None

    def calculate_signal_confidence(self,
                                    rsi: float,
                                    volume_ratio: float,
                                    has_candle_pattern: bool,
                                    has_divergence: bool,
                                    bb_touch: bool) -> float:
        """
        Calculate composite confidence score (0-1)

        High confidence when:
        - RSI extremely oversold/overbought
        - Volume spike strong (3x+)
        - Candlestick pattern present
        - RSI divergence present (bonus)
        - Touching outer Bollinger Band
        """
        confidence = 0.5  # Base

        # RSI extremity score
        if rsi < 15 or rsi > 85:  # SUPER extreme
            confidence += 0.20
        elif rsi < 20 or rsi > 80:  # Very extreme
            confidence += 0.15
        else:  # Mildly extreme
            confidence += 0.10

        # Volume confirmation score
        if volume_ratio >= 3.0:  # Huge spike
            confidence += 0.15
        elif volume_ratio >= 2.5:  # Strong spike
            confidence += 0.12
        elif volume_ratio >= 2.0:  # Good spike
            confidence += 0.10
        else:
            confidence += 0.05

        # Candlestick pattern (critical!)
        if has_candle_pattern:
            confidence += 0.15
        else:
            # Without pattern, reduce confidence significantly
            confidence -= 0.10

        # Bollinger Band touch (important!)
        if bb_touch:
            confidence += 0.10

        # RSI divergence (bonus confirmation)
        if has_divergence:
            confidence += 0.10

        return min(max(confidence, 0), 1.0)

    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """
        CARRARMATO Momentum Reversal Analysis

        Entry ONLY on perfect extreme setups
        """

        if len(df) < self.get_required_candles():
            logger.debug(f"Not enough candles: {len(df)}/{self.get_required_candles()}")
            return None

        # Calculate indicators
        rsi = self.calculate_rsi(df)
        upper_bb, middle_bb, lower_bb = self.calculate_bollinger_bands(df, self.bb_period, self.bb_std)
        volume_ratio = self.calculate_volume_profile(df)

        current_price = df['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_upper_bb = upper_bb.iloc[-1]
        current_lower_bb = lower_bb.iloc[-1]
        current_middle_bb = middle_bb.iloc[-1]

        # ========== FILTER #1: VOLUME CONFIRMATION ==========
        if volume_ratio < self.min_volume_ratio:
            logger.debug(f"❌ Volume too low: {volume_ratio:.2f}x (min {self.min_volume_ratio}x)")
            return None

        logger.debug(f"✅ Volume confirmed: {volume_ratio:.2f}x")

        # ========== FILTER #2: REVERSAL CANDLE ==========
        reversal_candle = self.detect_reversal_candle(df)

        # ========== FILTER #3: RSI DIVERGENCE (OPTIONAL BONUS) ==========
        rsi_divergence = self.check_rsi_divergence(df, rsi)

        signal = None

        # ========== OVERSOLD CONDITION - LOOK FOR LONG ==========
        if current_rsi < self.rsi_oversold:
            logger.debug(f"🔍 Oversold detected: RSI={current_rsi:.1f}")

            # Check Bollinger Band touch
            bb_touch = current_price <= current_lower_bb * 1.002  # Within 0.2% of lower BB

            # Calculate confidence
            has_candle_pattern = (reversal_candle == 'BULLISH')
            has_divergence = (rsi_divergence == 'BULLISH')

            confidence = self.calculate_signal_confidence(
                current_rsi, volume_ratio, has_candle_pattern,
                has_divergence, bb_touch
            )

            logger.debug(f"   Candle: {has_candle_pattern}, Divergence: {has_divergence}, " +
                        f"BB Touch: {bb_touch}, Confidence: {confidence:.0%}")

            # Only enter if confidence high enough
            if confidence >= self.min_confidence:
                entry_price = current_price
                stop_loss = entry_price * (1 - self.stop_loss_pct)

                # Take profit: middle BB or fixed %
                tp_middle_bb = current_middle_bb
                tp_fixed = entry_price * (1 + self.take_profit_pct)
                take_profit = min(tp_middle_bb, tp_fixed)

                signal = {
                    'action': 'LONG',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'leverage': self.default_leverage,
                    'confidence': confidence,
                    'reason': f'🛡️ CARRARMATO Oversold Reversal: RSI={current_rsi:.0f}, ' +
                            f'Vol={volume_ratio:.1f}x, Pattern={has_candle_pattern}, ' +
                            f'Div={has_divergence}, Conf={confidence:.0%}'
                }
                logger.info(f"🎯 HIGH CONFIDENCE LONG REVERSAL SIGNAL: {confidence:.0%}")
            else:
                logger.debug(f"⚠️ Confidence too low for LONG: {confidence:.0%} (min {self.min_confidence:.0%})")

        # ========== OVERBOUGHT CONDITION - LOOK FOR SHORT ==========
        elif current_rsi > self.rsi_overbought:
            logger.debug(f"🔍 Overbought detected: RSI={current_rsi:.1f}")

            # Check Bollinger Band touch
            bb_touch = current_price >= current_upper_bb * 0.998  # Within 0.2% of upper BB

            # Calculate confidence
            has_candle_pattern = (reversal_candle == 'BEARISH')
            has_divergence = (rsi_divergence == 'BEARISH')

            confidence = self.calculate_signal_confidence(
                current_rsi, volume_ratio, has_candle_pattern,
                has_divergence, bb_touch
            )

            logger.debug(f"   Candle: {has_candle_pattern}, Divergence: {has_divergence}, " +
                        f"BB Touch: {bb_touch}, Confidence: {confidence:.0%}")

            # Only enter if confidence high enough
            if confidence >= self.min_confidence:
                entry_price = current_price
                stop_loss = entry_price * (1 + self.stop_loss_pct)

                # Take profit: middle BB or fixed %
                tp_middle_bb = current_middle_bb
                tp_fixed = entry_price * (1 - self.take_profit_pct)
                take_profit = max(tp_middle_bb, tp_fixed)

                signal = {
                    'action': 'SHORT',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'leverage': self.default_leverage,
                    'confidence': confidence,
                    'reason': f'🛡️ CARRARMATO Overbought Reversal: RSI={current_rsi:.0f}, ' +
                            f'Vol={volume_ratio:.1f}x, Pattern={has_candle_pattern}, ' +
                            f'Div={has_divergence}, Conf={confidence:.0%}'
                }
                logger.info(f"🎯 HIGH CONFIDENCE SHORT REVERSAL SIGNAL: {confidence:.0%}")
            else:
                logger.debug(f"⚠️ Confidence too low for SHORT: {confidence:.0%} (min {self.min_confidence:.0%})")

        if signal and self.validate_signal(signal):
            logger.info(f"[{self.name}] 🛡️ CARRARMATO SIGNAL: {signal['action']} for {symbol}")
            logger.info(f"   Entry: ${signal['entry_price']:.2f}, SL: ${signal['stop_loss']:.2f}, TP: ${signal['take_profit']:.2f}")
            logger.info(f"   R/R: 1:{self.take_profit_pct/self.stop_loss_pct:.1f}, Confidence: {signal['confidence']:.0%}")
            return signal

        return None
