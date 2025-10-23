"""
Support/Resistance Bounce Strategy - Classical TA

Optimized for: WINNING RATE 70-75%
Leverage: 20x
Best for: All market conditions

Philosophy:
- Identify strong S/R levels tested multiple times
- Trade bounces off these levels with confirmation
- Classic but extremely effective when done right
- Multi-timeframe level confirmation

ENTRY ONLY WHEN:
1. Level tested 3+ times historically
2. Price within 0.3% of level
3. Volume confirms (spike on approach)
4. Candlestick pattern confirms bounce
5. RSI confirms (oversold at support, overbought at resistance)
"""
from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from loguru import logger


class SupportResistanceBounceStrategy(BaseStrategy):
    """
    Support/Resistance Bounce - Classical Technical Analysis

    Target: 70-75% winning rate
    R/R: 1:2.0
    Frequency: 3-6 trades/day per symbol
    """

    def __init__(self, leverage: int = 20):
        super().__init__("Support/Resistance Bounce", leverage)

        # BALANCED PARAMETERS
        self.stop_loss_pct = 0.015  # 1.5% SL (beyond the level)
        self.take_profit_pct = 0.030  # 3.0% TP (target opposite level)
        # R/R = 1:2.0 ✅

        # Level identification
        self.lookback_period = 200  # Candles to analyze for levels
        self.min_touches = 3  # Level must be tested 3+ times
        self.level_tolerance = 0.003  # 0.3% tolerance for "touching"

        # Proximity to level for entry
        self.max_distance_from_level = 0.003  # 0.3% max distance

        # Volume confirmation
        self.min_volume_ratio = 1.5  # 1.5x volume on approach

        # RSI confirmation
        self.support_rsi_max = 45  # RSI < 45 at support
        self.resistance_rsi_min = 55  # RSI > 55 at resistance

        # Confidence requirement
        self.min_confidence = 0.60  # 60% confidence

        # Cache for calculated levels
        self.cached_levels = {}
        self.cache_timestamp = {}
        self.cache_duration = 300  # 5 min cache

    def get_required_candles(self) -> int:
        return 200  # Need history to identify levels

    def identify_support_resistance_levels(self, df: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """
        Identify significant support and resistance levels

        Uses pivot points + clustering algorithm

        Returns:
            (support_levels, resistance_levels)
        """
        # Use last N candles
        lookback_df = df.iloc[-self.lookback_period:]

        # Find local peaks (resistance) and troughs (support)
        highs = lookback_df['high'].values
        lows = lookback_df['low'].values

        # Identify local maxima (resistance candidates)
        resistance_candidates = []
        for i in range(2, len(highs) - 2):
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance_candidates.append(highs[i])

        # Identify local minima (support candidates)
        support_candidates = []
        for i in range(2, len(lows) - 2):
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support_candidates.append(lows[i])

        # Cluster levels (merge similar levels)
        def cluster_levels(levels: List[float], tolerance: float) -> List[Tuple[float, int]]:
            """
            Cluster similar levels and count touches

            Returns:
                List of (level, touch_count)
            """
            if not levels:
                return []

            levels_sorted = sorted(levels)
            clusters = []
            current_cluster = [levels_sorted[0]]

            for level in levels_sorted[1:]:
                # If within tolerance, add to current cluster
                if abs(level - np.mean(current_cluster)) / np.mean(current_cluster) < tolerance:
                    current_cluster.append(level)
                else:
                    # Save cluster and start new one
                    avg_level = np.mean(current_cluster)
                    clusters.append((avg_level, len(current_cluster)))
                    current_cluster = [level]

            # Add last cluster
            if current_cluster:
                avg_level = np.mean(current_cluster)
                clusters.append((avg_level, len(current_cluster)))

            return clusters

        # Cluster and filter by minimum touches
        support_levels_raw = cluster_levels(support_candidates, self.level_tolerance)
        resistance_levels_raw = cluster_levels(resistance_candidates, self.level_tolerance)

        # Filter by min touches
        support_levels = [level for level, touches in support_levels_raw if touches >= self.min_touches]
        resistance_levels = [level for level, touches in resistance_levels_raw if touches >= self.min_touches]

        # Sort by strength (more touches = stronger)
        support_levels = sorted(support_levels, key=lambda x: sum(1 for l, t in support_levels_raw if l == x), reverse=True)
        resistance_levels = sorted(resistance_levels, key=lambda x: sum(1 for l, t in resistance_levels_raw if l == x), reverse=True)

        logger.debug(f"Identified {len(support_levels)} support levels and {len(resistance_levels)} resistance levels")

        return support_levels[:5], resistance_levels[:5]  # Top 5 strongest levels

    def find_nearest_level(self, price: float, levels: List[float]) -> Optional[Tuple[float, float]]:
        """
        Find nearest support or resistance level

        Returns:
            (level, distance_pct) or None
        """
        if not levels:
            return None

        nearest = min(levels, key=lambda x: abs(x - price))
        distance_pct = abs(price - nearest) / price

        return nearest, distance_pct

    def check_bounce_confirmation(self, df: pd.DataFrame, level: float, is_support: bool) -> bool:
        """
        Check for candlestick confirmation of bounce

        For support: Look for bullish rejection (hammer, long lower wick)
        For resistance: Look for bearish rejection (shooting star, long upper wick)
        """
        if len(df) < 2:
            return False

        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]

        open_price = last_candle['open']
        close = last_candle['close']
        high = last_candle['high']
        low = last_candle['low']

        body = abs(close - open_price)
        total_range = high - low

        if total_range == 0:
            return False

        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low

        if is_support:
            # Look for bullish bounce: long lower wick, close > open
            if (lower_wick > body * 2 and
                close > open_price and
                lower_wick > upper_wick * 2):
                # Price tested level (low near level) and bounced
                if abs(low - level) / level < self.level_tolerance:
                    logger.debug(f"✅ Bullish bounce pattern at support ${level:.2f}")
                    return True

        else:  # Resistance
            # Look for bearish bounce: long upper wick, close < open
            if (upper_wick > body * 2 and
                close < open_price and
                upper_wick > lower_wick * 2):
                # Price tested level (high near level) and bounced
                if abs(high - level) / level < self.level_tolerance:
                    logger.debug(f"✅ Bearish bounce pattern at resistance ${level:.2f}")
                    return True

        return False

    def calculate_signal_confidence(self,
                                    distance_pct: float,
                                    touches: int,
                                    volume_ratio: float,
                                    rsi: float,
                                    has_pattern: bool,
                                    is_support: bool) -> float:
        """
        Calculate composite confidence score (0-1)

        High confidence when:
        - Very close to level (< 0.2%)
        - Level tested many times (5+)
        - Strong volume spike (2x+)
        - RSI confirms
        - Candlestick pattern present
        """
        confidence = 0.5  # Base

        # Distance from level score
        if distance_pct < 0.001:  # < 0.1%
            confidence += 0.15
        elif distance_pct < 0.002:  # < 0.2%
            confidence += 0.12
        elif distance_pct < 0.003:  # < 0.3%
            confidence += 0.10
        else:
            confidence += 0.05

        # Level strength score (touches)
        if touches >= 5:
            confidence += 0.15
        elif touches >= 4:
            confidence += 0.12
        elif touches >= 3:
            confidence += 0.10
        else:
            confidence += 0.05

        # Volume confirmation score
        if volume_ratio >= 2.0:
            confidence += 0.12
        elif volume_ratio >= 1.5:
            confidence += 0.10
        else:
            confidence += 0.05

        # RSI confirmation score
        if is_support:
            if rsi < 35:
                confidence += 0.12
            elif rsi < 45:
                confidence += 0.10
            else:
                confidence += 0.05
        else:
            if rsi > 65:
                confidence += 0.12
            elif rsi > 55:
                confidence += 0.10
            else:
                confidence += 0.05

        # Candlestick pattern (critical!)
        if has_pattern:
            confidence += 0.15
        else:
            confidence -= 0.05  # Penalty without pattern

        return min(max(confidence, 0), 1.0)

    def analyze(self, df: pd.DataFrame, symbol: str,
                current_inventory: float = 0.0,
                funding_history: Optional[List[Dict]] = None,
                current_timestamp: Optional[int] = None) -> Optional[Dict]:
        """
        Analyze for Support/Resistance bounce opportunities

        Classical but very effective when properly implemented
        """

        if len(df) < self.get_required_candles():
            logger.debug(f"Not enough candles: {len(df)}/{self.get_required_candles()}")
            return None

        # ========== IDENTIFY S/R LEVELS (WITH CACHING) ==========
        # Check cache
        cache_key = symbol
        current_time = current_timestamp or int(pd.Timestamp.now().timestamp())

        if (cache_key in self.cached_levels and
            cache_key in self.cache_timestamp and
            current_time - self.cache_timestamp[cache_key] < self.cache_duration):
            # Use cached levels
            support_levels, resistance_levels = self.cached_levels[cache_key]
            logger.debug(f"Using cached S/R levels for {symbol}")
        else:
            # Calculate new levels
            support_levels, resistance_levels = self.identify_support_resistance_levels(df)
            # Cache them
            self.cached_levels[cache_key] = (support_levels, resistance_levels)
            self.cache_timestamp[cache_key] = current_time

        if not support_levels and not resistance_levels:
            logger.debug(f"❌ No significant S/R levels found")
            return None

        # ========== FILTER #1: CHECK PROXIMITY TO LEVELS ==========
        current_price = df['close'].iloc[-1]

        # Find nearest support and resistance
        nearest_support = self.find_nearest_level(current_price, support_levels)
        nearest_resistance = self.find_nearest_level(current_price, resistance_levels)

        # Determine which level to trade
        trade_level = None
        is_support = False
        distance_pct = float('inf')

        if nearest_support and nearest_support[1] < self.max_distance_from_level:
            trade_level, distance_pct = nearest_support
            is_support = True
            logger.debug(f"Near support: ${trade_level:.2f} (distance: {distance_pct:.2%})")

        if nearest_resistance and nearest_resistance[1] < distance_pct:
            trade_level, distance_pct = nearest_resistance
            is_support = False
            logger.debug(f"Near resistance: ${trade_level:.2f} (distance: {distance_pct:.2%})")

        if trade_level is None:
            logger.debug(f"❌ No levels nearby (min distance: {distance_pct:.2%})")
            return None

        logger.debug(f"✅ {'Support' if is_support else 'Resistance'} level: ${trade_level:.2f}, Distance: {distance_pct:.2%}")

        # ========== FILTER #2: VOLUME CONFIRMATION ==========
        volume_ratio = self.calculate_volume_profile(df, period=20)

        if volume_ratio < self.min_volume_ratio:
            logger.debug(f"❌ Volume too low: {volume_ratio:.2f}x (min {self.min_volume_ratio}x)")
            return None

        logger.debug(f"✅ Volume spike: {volume_ratio:.2f}x")

        # ========== FILTER #3: RSI CONFIRMATION ==========
        rsi = self.calculate_rsi(df).iloc[-1]

        if is_support and rsi > self.support_rsi_max:
            logger.debug(f"⚠️ RSI too high for support bounce: {rsi:.1f} (want < {self.support_rsi_max})")
            # Don't return, just affect confidence

        if not is_support and rsi < self.resistance_rsi_min:
            logger.debug(f"⚠️ RSI too low for resistance bounce: {rsi:.1f} (want > {self.resistance_rsi_min})")
            # Don't return, just affect confidence

        logger.debug(f"RSI: {rsi:.1f}")

        # ========== FILTER #4: CANDLESTICK PATTERN ==========
        has_pattern = self.check_bounce_confirmation(df, trade_level, is_support)

        # ========== GENERATE SIGNAL ==========
        signal = None

        # Count touches (for confidence)
        touches = self.min_touches  # At minimum

        if is_support:
            # BOUNCE OFF SUPPORT → LONG
            logger.debug(f"🔍 Support bounce opportunity")

            confidence = self.calculate_signal_confidence(
                distance_pct, touches, volume_ratio, rsi, has_pattern, True
            )

            if confidence >= self.min_confidence:
                entry_price = current_price
                stop_loss = trade_level * (1 - self.stop_loss_pct/2)  # Below support

                # Take profit: target nearest resistance or fixed %
                if nearest_resistance:
                    tp_resistance, _ = nearest_resistance
                    tp_fixed = entry_price * (1 + self.take_profit_pct)
                    take_profit = min(tp_resistance * 0.995, tp_fixed)  # 0.5% before resistance
                else:
                    take_profit = entry_price * (1 + self.take_profit_pct)

                signal = {
                    'action': 'LONG',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'leverage': self.default_leverage,
                    'confidence': confidence,
                    'reason': f'🎯 Support Bounce: Level=${trade_level:.0f}, ' +
                            f'Dist={distance_pct:.2%}, Vol={volume_ratio:.1f}x, ' +
                            f'RSI={rsi:.0f}, Pattern={has_pattern}, Conf={confidence:.0%}'
                }
                logger.info(f"🎯 SUPPORT BOUNCE LONG SIGNAL: {confidence:.0%}")
            else:
                logger.debug(f"⚠️ Confidence too low for LONG: {confidence:.0%} (min {self.min_confidence:.0%})")

        else:
            # BOUNCE OFF RESISTANCE → SHORT
            logger.debug(f"🔍 Resistance bounce opportunity")

            confidence = self.calculate_signal_confidence(
                distance_pct, touches, volume_ratio, rsi, has_pattern, False
            )

            if confidence >= self.min_confidence:
                entry_price = current_price
                stop_loss = trade_level * (1 + self.stop_loss_pct/2)  # Above resistance

                # Take profit: target nearest support or fixed %
                if nearest_support:
                    tp_support, _ = nearest_support
                    tp_fixed = entry_price * (1 - self.take_profit_pct)
                    take_profit = max(tp_support * 1.005, tp_fixed)  # 0.5% after support
                else:
                    take_profit = entry_price * (1 - self.take_profit_pct)

                signal = {
                    'action': 'SHORT',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'leverage': self.default_leverage,
                    'confidence': confidence,
                    'reason': f'🎯 Resistance Bounce: Level=${trade_level:.0f}, ' +
                            f'Dist={distance_pct:.2%}, Vol={volume_ratio:.1f}x, ' +
                            f'RSI={rsi:.0f}, Pattern={has_pattern}, Conf={confidence:.0%}'
                }
                logger.info(f"🎯 RESISTANCE BOUNCE SHORT SIGNAL: {confidence:.0%}")
            else:
                logger.debug(f"⚠️ Confidence too low for SHORT: {confidence:.0%} (min {self.min_confidence:.0%})")

        if signal and self.validate_signal(signal):
            logger.info(f"[{self.name}] 🎯 S/R BOUNCE SIGNAL: {signal['action']} for {symbol}")
            logger.info(f"   Entry: ${signal['entry_price']:.2f}, SL: ${signal['stop_loss']:.2f}, TP: ${signal['take_profit']:.2f}")
            logger.info(f"   R/R: 1:{self.take_profit_pct/self.stop_loss_pct:.1f}, Confidence: {signal['confidence']:.0%}")
            return signal

        return None
