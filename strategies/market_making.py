"""
CARRARMATO Market Making Strategy - Ultra Conservative

Optimized for: WINNING RATE 75%+
Leverage: 15x (conservative)
Best for: Stable range-bound markets with clear support/resistance

Philosophy:
- FEW trades, but ALMOST ALWAYS winners
- R/R minimum 1:2.5 (ogni win copre 2.5 loss)
- 5+ confirmation filters before entry
- Stop loss strettissimo (1.0%)
- Take profit generoso (2.5%)
- NO entries in condizioni incerte

ENTRY ONLY WHEN:
1. Volatility in range sicuro (1.5% - 4.0%)
2. Volume stabile (0.8x - 2.0x media)
3. RSI in zona neutrale (35-65)
4. NO trend forte (< 2.5%)
5. Spread favorevole
6. Fair value confermato da VWAP
"""
from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from loguru import logger


class MarketMakingStrategy(BaseStrategy):
    """
    CARRARMATO Market Making - Ultra High Win Rate

    Target: 75%+ winning rate
    R/R: 1:2.5
    Max Daily Trades: 3-4
    """

    def __init__(self, leverage: int = 3):  # MODIFICATO: Era 15, ora 3 per sicurezza
        super().__init__("Market Making", leverage)

        # ULTRA-SAFE PARAMETERS - Post-Loss Recovery Mode
        self.spread_target = 0.008  # 0.8% target spread (più ampio)
        self.min_spread = 0.006  # 0.6% minimum spread (più ampio)
        self.max_spread = 0.015  # 1.5% maximum spread (più ampio)

        # R/R = 1:2.0 (Con leverage basso, SL/TP più ampi)
        self.stop_loss_pct = 0.020  # 2.0% SL (era 1.0%) - Con leverage 3x = 6% perdita
        self.take_profit_pct = 0.040  # 4.0% TP (era 2.5%) - Con leverage 3x = 12% gain

        # Volatility range (RESTRITTIVO - solo mercati stabili)
        self.min_volatility = 0.015  # 1.5% (più alto)
        self.max_volatility = 0.035  # 3.5% (più basso) - Evita alta volatilità

        # Volume filter (RESTRITTIVO - no anomalie)
        self.min_volume_ratio = 0.8  # Min 80% della media (più alto)
        self.max_volume_ratio = 1.5  # Max 1.5x della media (MOLTO più basso) - No pump/dump

        # RSI filter (RESTRITTIVO - solo neutrale)
        self.rsi_min = 40  # Era 30 (più alto)
        self.rsi_max = 60  # Era 70 (più basso)

        # Trend filter (MOLTO RESTRITTIVO - solo ranging)
        self.max_trend_strength = 1.5  # < 1.5% = OK (era 3.5%) - SOLO mercati laterali!

        # Entry window (PIÙ STRETTO - più selettivo)
        self.entry_tolerance = 0.015  # 1.5% (era 2.0%)

        # Inventory management (PIÙ CONSERVATIVO)
        self.inventory_limit = 0.3  # Max 30% bias (era 40%)

        # Confidence requirement (PIÙ ALTO - solo segnali ottimi)
        self.min_confidence = 0.70  # Minimo 70% confidence (era 55%)

    def get_required_candles(self) -> int:
        return 100  # Più dati = più sicurezza

    def calculate_fair_value(self, df: pd.DataFrame) -> float:
        """
        Calculate fair value using VWAP + EMA combination
        More robust than pure VWAP
        """
        if len(df) < 20:
            return df['close'].iloc[-1]

        # VWAP degli ultimi 20 candles
        recent_df = df.iloc[-20:]
        vwap = (recent_df['close'] * recent_df['volume']).sum() / recent_df['volume'].sum()

        # EMA 20
        ema_20 = self.calculate_ema(df, 20).iloc[-1]

        # Weighted average: 60% VWAP, 40% EMA
        fair_value = (vwap * 0.6) + (ema_20 * 0.4)

        return fair_value

    def check_volume_conditions(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """
        Check if volume is in acceptable range

        Returns:
            (is_valid, volume_ratio)
        """
        volume_ratio = self.calculate_volume_profile(df, period=20)

        # Troppo basso = low liquidity
        if volume_ratio < self.min_volume_ratio:
            logger.debug(f"Volume too low: {volume_ratio:.2f}x")
            return False, volume_ratio

        # Troppo alto = possibili anomalie o dump/pump
        if volume_ratio > self.max_volume_ratio:
            logger.debug(f"Volume too high (anomaly): {volume_ratio:.2f}x")
            return False, volume_ratio

        return True, volume_ratio

    def check_rsi_neutral(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """
        Check if RSI is in neutral zone (not overbought/oversold)

        Returns:
            (is_neutral, rsi_value)
        """
        rsi = self.calculate_rsi(df, period=14).iloc[-1]

        if rsi < self.rsi_min or rsi > self.rsi_max:
            logger.debug(f"RSI out of neutral zone: {rsi:.1f}")
            return False, rsi

        return True, rsi

    def check_trend_strength(self, df: pd.DataFrame) -> Tuple[bool, float, Optional[str]]:
        """
        Check if trend is weak enough for market making

        Returns:
            (is_acceptable, trend_strength_pct, direction)
        """
        is_trending, direction = self.is_trending(df, period=50)

        if not is_trending:
            return True, 0.0, None

        # Calculate actual trend strength
        ema_short = self.calculate_ema(df, 25).iloc[-1]
        ema_long = self.calculate_ema(df, 50).iloc[-1]
        trend_strength = abs(ema_short - ema_long) / ema_long * 100

        if trend_strength > self.max_trend_strength:
            logger.debug(f"Trend too strong: {trend_strength:.2f}% {direction}")
            return False, trend_strength, direction

        # Trend debole = acceptable
        return True, trend_strength, direction

    def calculate_optimal_spread(self, df: pd.DataFrame, volatility: float) -> Tuple[float, float]:
        """
        Calculate optimal bid/ask spread based on market conditions
        CARRARMATO: spread più ampi = più sicurezza
        """
        # Base spread (più ampio del vecchio)
        spread = self.spread_target

        # Adjust for volatility (più vol = spread più ampio)
        if volatility > 0.03:
            spread *= 1.8  # +80% in high vol
        elif volatility < 0.02:
            spread *= 1.2  # +20% in low vol (mantieni margine)

        # Ensure within limits
        spread = max(self.min_spread, min(spread, self.max_spread))

        # Split spread evenly
        bid_offset = spread / 2
        ask_offset = spread / 2

        return bid_offset, ask_offset

    def calculate_signal_confidence(self,
                                    volatility: float,
                                    volume_ratio: float,
                                    rsi: float,
                                    trend_strength: float,
                                    price_distance: float) -> float:
        """
        Calculate composite confidence score (0-1)

        High confidence when:
        - Volatility in sweet spot (2-3%)
        - Volume normal (1.0-1.5x)
        - RSI near 50
        - No strong trend
        - Price near fair value
        """
        confidence = 0.5  # Base

        # Volatility score (sweet spot = 2-3%)
        if 0.02 <= volatility <= 0.03:
            confidence += 0.15
        elif 0.015 <= volatility <= 0.035:
            confidence += 0.10
        else:
            confidence += 0.05

        # Volume score (sweet spot = 1.0-1.3x)
        if 1.0 <= volume_ratio <= 1.3:
            confidence += 0.15
        elif 0.8 <= volume_ratio <= 1.8:
            confidence += 0.10
        else:
            confidence += 0.05

        # RSI score (sweet spot = 45-55)
        rsi_distance = abs(rsi - 50)
        if rsi_distance < 5:
            confidence += 0.15
        elif rsi_distance < 10:
            confidence += 0.10
        else:
            confidence += 0.05

        # Trend score (no trend = best)
        if trend_strength < 1.0:
            confidence += 0.10
        elif trend_strength < 2.0:
            confidence += 0.05

        # Price distance score (closer to fair value = better)
        if price_distance < 0.005:  # < 0.5%
            confidence += 0.10
        elif price_distance < 0.010:  # < 1.0%
            confidence += 0.05

        return min(confidence, 1.0)

    def analyze(self, df: pd.DataFrame, symbol: str,
                current_inventory: float = 0.0,
                funding_history: Optional[List[Dict]] = None) -> Optional[Dict]:
        """
        CARRARMATO Analysis - Multiple confirmation filters

        Entry ONLY if ALL conditions pass
        """

        if len(df) < self.get_required_candles():
            logger.debug(f"Not enough candles: {len(df)}/{self.get_required_candles()}")
            return None

        # ========== FILTER #1: VOLATILITY ==========
        volatility = self.calculate_volatility(df, period=20)

        if volatility < self.min_volatility:
            logger.debug(f"❌ Volatility too low: {volatility*100:.2f}% (min {self.min_volatility*100}%)")
            return None

        if volatility > self.max_volatility:
            logger.debug(f"❌ Volatility too high: {volatility*100:.2f}% (max {self.max_volatility*100}%)")
            return None

        logger.debug(f"✅ Volatility OK: {volatility*100:.2f}%")

        # ========== FILTER #2: VOLUME ==========
        volume_ok, volume_ratio = self.check_volume_conditions(df)
        if not volume_ok:
            return None

        logger.debug(f"✅ Volume OK: {volume_ratio:.2f}x")

        # ========== FILTER #3: RSI NEUTRAL ==========
        rsi_ok, rsi = self.check_rsi_neutral(df)
        if not rsi_ok:
            return None

        logger.debug(f"✅ RSI Neutral: {rsi:.1f}")

        # ========== FILTER #4: TREND WEAK ==========
        trend_ok, trend_strength, trend_direction = self.check_trend_strength(df)
        if not trend_ok:
            return None

        logger.debug(f"✅ Trend OK: {trend_strength:.2f}% {trend_direction or 'ranging'}")

        # ========== FILTER #5: FAIR VALUE & SPREAD ==========
        fair_value = self.calculate_fair_value(df)
        current_price = df['close'].iloc[-1]

        bid_offset, ask_offset = self.calculate_optimal_spread(df, volatility)

        # Calculate entry prices
        inventory_adjustment = current_inventory * 0.003  # 0.3% per 10% inventory

        signal = None

        # ========== LONG OPPORTUNITY ==========
        if current_inventory < self.inventory_limit:
            entry_price = fair_value * (1 - bid_offset - inventory_adjustment)
            stop_loss = entry_price * (1 - self.stop_loss_pct)
            take_profit = entry_price * (1 + self.take_profit_pct)

            # Check if price is within entry tolerance
            price_distance = abs(current_price - entry_price) / current_price

            if price_distance < self.entry_tolerance:
                # Calculate confidence
                confidence = self.calculate_signal_confidence(
                    volatility, volume_ratio, rsi, trend_strength, price_distance
                )

                # Only enter if confidence high enough
                if confidence >= self.min_confidence:
                    signal = {
                        'action': 'LONG',
                        'entry_price': current_price,  # Use current price for market order
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'leverage': self.default_leverage,
                        'confidence': confidence,
                        'reason': f'🛡️ CARRARMATO BID: FV=${fair_value:.2f}, ' +
                                f'Vol={volatility*100:.2f}%, RSI={rsi:.0f}, ' +
                                f'VolRatio={volume_ratio:.2f}x, Conf={confidence:.0%}'
                    }
                    logger.info(f"🎯 HIGH CONFIDENCE LONG SIGNAL: {confidence:.0%}")
                else:
                    logger.debug(f"⚠️ Confidence too low for LONG: {confidence:.0%} (min {self.min_confidence:.0%})")

        # ========== SHORT OPPORTUNITY ==========
        elif current_inventory > -self.inventory_limit:
            entry_price = fair_value * (1 + ask_offset - inventory_adjustment)
            stop_loss = entry_price * (1 + self.stop_loss_pct)
            take_profit = entry_price * (1 - self.take_profit_pct)

            # Check if price is within entry tolerance
            price_distance = abs(current_price - entry_price) / current_price

            if price_distance < self.entry_tolerance:
                # Calculate confidence
                confidence = self.calculate_signal_confidence(
                    volatility, volume_ratio, rsi, trend_strength, price_distance
                )

                # Only enter if confidence high enough
                if confidence >= self.min_confidence:
                    signal = {
                        'action': 'SHORT',
                        'entry_price': current_price,  # Use current price for market order
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'leverage': self.default_leverage,
                        'confidence': confidence,
                        'reason': f'🛡️ CARRARMATO ASK: FV=${fair_value:.2f}, ' +
                                f'Vol={volatility*100:.2f}%, RSI={rsi:.0f}, ' +
                                f'VolRatio={volume_ratio:.2f}x, Conf={confidence:.0%}'
                    }
                    logger.info(f"🎯 HIGH CONFIDENCE SHORT SIGNAL: {confidence:.0%}")
                else:
                    logger.debug(f"⚠️ Confidence too low for SHORT: {confidence:.0%} (min {self.min_confidence:.0%})")

        if signal and self.validate_signal(signal):
            logger.info(f"[{self.name}] 🛡️ CARRARMATO SIGNAL: {signal['action']} for {symbol}")
            logger.info(f"   Entry: ${signal['entry_price']:.2f}, SL: ${signal['stop_loss']:.2f}, TP: ${signal['take_profit']:.2f}")
            logger.info(f"   R/R: 1:{self.take_profit_pct/self.stop_loss_pct:.1f}, Confidence: {signal['confidence']:.0%}")
            return signal

        return None
