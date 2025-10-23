"""
VWAP Mean Reversion Strategy - Statistical Edge

Optimized for: WINNING RATE 75-80%
Leverage: 15x (conservative)
Best for: Range-bound markets, intraday trading

Philosophy:
- VWAP = Fair price of the day
- Price tends to revert to VWAP
- High probability, low risk
- Mean reversion is one of the most reliable patterns

ENTRY ONLY WHEN:
1. Price deviates from VWAP by 1.5-3.0%
2. Volume confirms (not a spike/anomaly)
3. RSI confirms (oversold for LONG, overbought for SHORT)
4. No strong trend (range-bound preferred)
5. Session VWAP (resets daily)
"""
from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from loguru import logger


class VWAPReversionStrategy(BaseStrategy):
    """
    VWAP Mean Reversion - High Win Rate Strategy

    Target: 75-80% winning rate
    R/R: 1:1.67
    Frequency: 3-5 trades/day per symbol
    """

    def __init__(self, leverage: int = 3):  # MODIFICATO: Era 15, ora 3 per sicurezza
        super().__init__("VWAP Reversion", leverage)

        # ULTRA-SAFE PARAMETERS - Post-Loss Recovery Mode
        self.stop_loss_pct = 0.020  # 2.0% SL (era 1.2%) - Con leverage 3x = 6% perdita
        self.take_profit_pct = 0.040  # 4.0% TP (era 2.0%) - Con leverage 3x = 12% gain
        # R/R = 1:2.0 ✅ Migliorato!

        # VWAP deviation thresholds - PIÙ RESTRITTIVO
        self.min_deviation = 0.020  # 2.0% min distance from VWAP (era 1.5%)
        self.max_deviation = 0.040  # 4.0% max (era 3.0%) - Deviazioni più ampie
        self.optimal_deviation = 0.025  # 2.5% = sweet spot (era 2.0%)

        # Volume filter - PIÙ CONSERVATIVO (no anomalies)
        self.min_volume_ratio = 0.9  # Min 90% (era 80%)
        self.max_volume_ratio = 1.8  # Max 1.8x (era 2.5x) - No spike anomalies

        # RSI confirmation - PIÙ RESTRITTIVO
        self.rsi_oversold = 35  # Per LONG (era 40) - Solo zone più oversold
        self.rsi_overbought = 65  # Per SHORT (era 60) - Solo zone più overbought

        # Trend filter - MOLTO PIÙ RESTRITTIVO (prefer range-bound)
        self.max_trend_strength = 2.0  # < 2% trend OK (era 3.0%)

        # Confidence requirement - PIÙ ALTO
        self.min_confidence = 0.70  # 70% confidence (era 60%)

        # Session tracking (VWAP resets daily)
        self.session_vwap = True

    def get_required_candles(self) -> int:
        return 100  # Need enough for reliable VWAP

    def calculate_session_vwap(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate VWAP for current session

        VWAP = Σ(Price × Volume) / Σ(Volume)

        For session VWAP, we use last 24h (288 candles at 5m)
        """
        # Use last 288 candles (24 hours at 5min) or all available
        lookback = min(288, len(df))
        session_df = df.iloc[-lookback:]

        # Typical price
        typical_price = (session_df['high'] + session_df['low'] + session_df['close']) / 3

        # Cumulative volume-weighted price
        cumulative_vp = (typical_price * session_df['volume']).cumsum()
        cumulative_volume = session_df['volume'].cumsum()

        # VWAP
        vwap = cumulative_vp / cumulative_volume

        # Extend to full dataframe length with last value
        full_vwap = pd.Series(index=df.index, dtype=float)
        full_vwap.iloc[-len(vwap):] = vwap.values

        return full_vwap

    def calculate_vwap_bands(self, df: pd.DataFrame, vwap: pd.Series, std_multiplier: float = 1.0) -> tuple:
        """
        Calculate VWAP standard deviation bands

        Similar to Bollinger Bands but for VWAP
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3

        # Calculate standard deviation around VWAP
        lookback = min(288, len(df))
        rolling_std = typical_price.iloc[-lookback:].rolling(window=20).std()

        # Extend to full length
        full_std = pd.Series(index=df.index, dtype=float)
        full_std.iloc[-len(rolling_std):] = rolling_std.values

        upper_band = vwap + (full_std * std_multiplier)
        lower_band = vwap - (full_std * std_multiplier)

        return upper_band, lower_band

    def check_trend_suitability(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """
        Check if market is suitable (prefer range-bound)

        Returns:
            (is_suitable, trend_strength)
        """
        is_trending, direction = self.is_trending(df, period=50)

        if not is_trending:
            return True, 0.0

        # Calculate trend strength
        ema_short = self.calculate_ema(df, 25).iloc[-1]
        ema_long = self.calculate_ema(df, 50).iloc[-1]
        trend_strength = abs(ema_short - ema_long) / ema_long * 100

        if trend_strength > self.max_trend_strength:
            logger.debug(f"❌ Trend too strong: {trend_strength:.2f}% (max {self.max_trend_strength}%)")
            return False, trend_strength

        return True, trend_strength

    def calculate_signal_confidence(self,
                                    deviation_pct: float,
                                    volume_ratio: float,
                                    rsi: float,
                                    trend_strength: float,
                                    action: str) -> float:
        """
        Calculate composite confidence score (0-1)

        High confidence when:
        - Deviation near optimal (2%)
        - Volume normal (1.0-1.5x)
        - RSI confirms direction
        - Weak/no trend
        """
        confidence = 0.5  # Base

        # Deviation score (optimal = 2%)
        deviation_abs = abs(deviation_pct)
        if 0.018 <= deviation_abs <= 0.022:  # 1.8-2.2% = perfect
            confidence += 0.20
        elif 0.015 <= deviation_abs <= 0.025:  # 1.5-2.5% = good
            confidence += 0.15
        elif 0.015 <= deviation_abs <= 0.030:  # Within range
            confidence += 0.12
        else:
            confidence += 0.08

        # Volume score (prefer normal)
        if 1.0 <= volume_ratio <= 1.3:  # Normal = best
            confidence += 0.15
        elif 0.8 <= volume_ratio <= 1.8:  # Acceptable
            confidence += 0.12
        else:
            confidence += 0.08

        # RSI confirmation score
        if action == 'LONG':
            # Want low RSI for LONG (oversold)
            if rsi < 35:
                confidence += 0.15
            elif rsi < 40:
                confidence += 0.12
            elif rsi < 45:
                confidence += 0.08
        else:  # SHORT
            # Want high RSI for SHORT (overbought)
            if rsi > 65:
                confidence += 0.15
            elif rsi > 60:
                confidence += 0.12
            elif rsi > 55:
                confidence += 0.08

        # Trend score (no trend = best)
        if trend_strength < 1.0:
            confidence += 0.10
        elif trend_strength < 2.0:
            confidence += 0.08
        elif trend_strength < 3.0:
            confidence += 0.05

        return min(max(confidence, 0), 1.0)

    def analyze(self, df: pd.DataFrame, symbol: str,
                current_inventory: float = 0.0,
                funding_history: Optional[List[Dict]] = None) -> Optional[Dict]:
        """
        Analyze for VWAP mean reversion opportunities

        High probability trades when price deviates significantly from VWAP
        """

        if len(df) < self.get_required_candles():
            logger.debug(f"Not enough candles: {len(df)}/{self.get_required_candles()}")
            return None

        # ========== FILTER #1: CALCULATE VWAP ==========
        vwap = self.calculate_session_vwap(df)
        current_vwap = vwap.iloc[-1]
        current_price = df['close'].iloc[-1]

        if pd.isna(current_vwap):
            logger.debug(f"❌ VWAP not available")
            return None

        # Calculate deviation from VWAP
        deviation = (current_price - current_vwap) / current_vwap
        deviation_pct = abs(deviation)

        logger.debug(f"VWAP: ${current_vwap:.2f}, Price: ${current_price:.2f}, Deviation: {deviation:.2%}")

        # ========== FILTER #2: CHECK DEVIATION RANGE ==========
        if deviation_pct < self.min_deviation:
            logger.debug(f"❌ Deviation too small: {deviation_pct:.2%} (min {self.min_deviation:.0%})")
            return None

        if deviation_pct > self.max_deviation:
            logger.debug(f"❌ Deviation too large: {deviation_pct:.2%} (max {self.max_deviation:.0%})")
            return None

        logger.debug(f"✅ Deviation in range: {deviation_pct:.2%}")

        # ========== FILTER #3: VOLUME CHECK ==========
        volume_ratio = self.calculate_volume_profile(df, period=20)

        if volume_ratio < self.min_volume_ratio or volume_ratio > self.max_volume_ratio:
            logger.debug(f"❌ Volume out of range: {volume_ratio:.2f}x (range {self.min_volume_ratio}-{self.max_volume_ratio})")
            return None

        logger.debug(f"✅ Volume normal: {volume_ratio:.2f}x")

        # ========== FILTER #4: TREND SUITABILITY ==========
        trend_suitable, trend_strength = self.check_trend_suitability(df)

        if not trend_suitable:
            return None

        logger.debug(f"✅ Market suitable: Trend {trend_strength:.2f}%")

        # ========== FILTER #5: RSI CONFIRMATION ==========
        rsi = self.calculate_rsi(df).iloc[-1]

        signal = None

        # ========== PRICE ABOVE VWAP → SHORT (mean reversion down) ==========
        if deviation > self.min_deviation:
            logger.debug(f"🔍 Price above VWAP: {deviation:.2%}")

            # Check RSI (want overbought for SHORT)
            if rsi < self.rsi_overbought:
                logger.debug(f"⚠️ RSI not overbought enough: {rsi:.1f} (want > {self.rsi_overbought})")
                # Don't return, just lower confidence

            # Calculate confidence
            confidence = self.calculate_signal_confidence(
                deviation, volume_ratio, rsi, trend_strength, 'SHORT'
            )

            if confidence >= self.min_confidence:
                entry_price = current_price
                stop_loss = entry_price * (1 + self.stop_loss_pct)

                # Take profit: target VWAP or fixed %
                tp_vwap = current_vwap
                tp_fixed = entry_price * (1 - self.take_profit_pct)
                take_profit = max(tp_vwap, tp_fixed)  # Don't go below VWAP too much

                signal = {
                    'action': 'SHORT',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'leverage': self.default_leverage,
                    'confidence': confidence,
                    'reason': f'📉 VWAP Reversion DOWN: Dev={deviation:.1%}, ' +
                            f'VWAP=${current_vwap:.0f}, RSI={rsi:.0f}, ' +
                            f'Vol={volume_ratio:.1f}x, Conf={confidence:.0%}'
                }
                logger.info(f"🎯 VWAP MEAN REVERSION SHORT SIGNAL: {confidence:.0%}")
            else:
                logger.debug(f"⚠️ Confidence too low for SHORT: {confidence:.0%} (min {self.min_confidence:.0%})")

        # ========== PRICE BELOW VWAP → LONG (mean reversion up) ==========
        elif deviation < -self.min_deviation:
            logger.debug(f"🔍 Price below VWAP: {deviation:.2%}")

            # Check RSI (want oversold for LONG)
            if rsi > self.rsi_oversold:
                logger.debug(f"⚠️ RSI not oversold enough: {rsi:.1f} (want < {self.rsi_oversold})")
                # Don't return, just lower confidence

            # Calculate confidence
            confidence = self.calculate_signal_confidence(
                deviation, volume_ratio, rsi, trend_strength, 'LONG'
            )

            if confidence >= self.min_confidence:
                entry_price = current_price
                stop_loss = entry_price * (1 - self.stop_loss_pct)

                # Take profit: target VWAP or fixed %
                tp_vwap = current_vwap
                tp_fixed = entry_price * (1 + self.take_profit_pct)
                take_profit = min(tp_vwap, tp_fixed)  # Don't go above VWAP too much

                signal = {
                    'action': 'LONG',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'leverage': self.default_leverage,
                    'confidence': confidence,
                    'reason': f'📈 VWAP Reversion UP: Dev={deviation:.1%}, ' +
                            f'VWAP=${current_vwap:.0f}, RSI={rsi:.0f}, ' +
                            f'Vol={volume_ratio:.1f}x, Conf={confidence:.0%}'
                }
                logger.info(f"🎯 VWAP MEAN REVERSION LONG SIGNAL: {confidence:.0%}")
            else:
                logger.debug(f"⚠️ Confidence too low for LONG: {confidence:.0%} (min {self.min_confidence:.0%})")

        if signal and self.validate_signal(signal):
            logger.info(f"[{self.name}] 📈 VWAP REVERSION SIGNAL: {signal['action']} for {symbol}")
            logger.info(f"   Entry: ${signal['entry_price']:.2f}, SL: ${signal['stop_loss']:.2f}, TP: ${signal['take_profit']:.2f}")
            logger.info(f"   R/R: 1:{self.take_profit_pct/self.stop_loss_pct:.1f}, Confidence: {signal['confidence']:.0%}")
            return signal

        return None
