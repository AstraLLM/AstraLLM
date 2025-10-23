"""
CARRARMATO Breakout Scalping Strategy - Ultra High Precision

Optimized for: WINNING RATE 75%+
Leverage: 20x (moderate with excellent R/R)
Best for: Volatile markets with clear breakouts + volume confirmation

Philosophy:
- Wait for TRUE breakouts with multiple confirmations
- Volume spike 3x+ (not fake breakouts)
- RSI not extreme (avoid exhaustion)
- Clean consolidation before breakout
- R/R minimum 1:2.5

ENTRY ONLY WHEN:
1. Tight consolidation (ATR < 2% of price)
2. MASSIVE volume spike (3x+ average)
3. Clean breakout above/below consolidation zone
4. RSI in healthy range (30-70)
5. No recent false breakouts
"""
from typing import Dict, Optional
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from loguru import logger


class BreakoutScalpingStrategy(BaseStrategy):
    """
    CARRARMATO Breakout Scalping - Ultra High Win Rate

    Target: 75%+ winning rate
    R/R: 1:2.5
    Max Daily Trades: 3-4
    """

    def __init__(self, leverage: int = 5):  # MODIFICATO: Era 20, ora 5 per sicurezza
        super().__init__("Breakout Scalping", leverage)

        # ULTRA-SAFE PARAMETERS - Post-Loss Recovery Mode
        self.consolidation_period = 30  # Era 25 - AUMENTATO (più restrittivo)
        self.volume_multiplier = 4.0  # Era 2.0 - RADDOPPIATO! Solo breakout VERI con volume massiccio
        self.breakout_threshold = 0.008  # 0.8% (era 0.6%) - Breakout più significativi

        # R/R = 1:2.67 (Con leverage basso, SL/TP più ampi)
        self.stop_loss_pct = 0.015  # 1.5% SL (era 1.0%) - Con leverage 5x = 7.5% perdita
        self.take_profit_pct = 0.040  # 4.0% TP (era 2.5%) - Con leverage 5x = 20% gain

        # ATR limit (consolidation check) - MOLTO RESTRITTIVO
        self.max_atr_pct = 1.5  # 1.5% max (era 2.5%) - Solo consolidazioni MOLTO strette

        # RSI filter - RESTRITTIVO (range sano)
        self.rsi_min = 35  # Era 25 (più alto) - No zone estreme
        self.rsi_max = 65  # Era 75 (più basso) - No zone estreme

        # Confidence requirement (MOLTO ALTO - solo segnali ottimi)
        self.min_confidence = 0.75  # Minimo 75% confidence (era 60%) - Top 25% segnali

    def get_required_candles(self) -> int:
        return 100  # Più dati = più sicurezza

    def check_false_breakout_history(self, df: pd.DataFrame) -> bool:
        """
        Check if there were recent false breakouts
        Returns True if NO false breakouts (safe to trade)
        """
        if len(df) < 40:
            return True

        # Look at last 20 candles for false breakouts
        recent_df = df.iloc[-40:-10]  # Skip very recent (last 10)

        # Calculate range
        recent_high = recent_df['high'].max()
        recent_low = recent_df['low'].min()
        range_size = recent_high - recent_low

        # Count how many times price broke out and reversed
        false_breakouts = 0
        for i in range(len(recent_df) - 5):
            window = recent_df.iloc[i:i+5]

            # Check if price broke above and then reversed
            if window['high'].max() > recent_high * 1.005:  # Broke up 0.5%
                if window['close'].iloc[-1] < recent_high * 0.995:  # Reversed down
                    false_breakouts += 1

            # Check if price broke below and then reversed
            if window['low'].min() < recent_low * 0.995:  # Broke down 0.5%
                if window['close'].iloc[-1] > recent_low * 1.005:  # Reversed up
                    false_breakouts += 1

        # More than 2 false breakouts = risky
        if false_breakouts > 2:
            logger.debug(f"❌ Too many false breakouts detected: {false_breakouts}")
            return False

        return True

    def calculate_signal_confidence(self,
                                    volume_ratio: float,
                                    atr_pct: float,
                                    rsi: float,
                                    breakout_strength: float,
                                    no_false_breakouts: bool) -> float:
        """
        Calculate composite confidence score (0-1)

        High confidence when:
        - Massive volume spike (4x+)
        - Tight consolidation (ATR < 1.5%)
        - RSI in healthy range (40-60)
        - Strong breakout (> 1%)
        - No recent false breakouts
        """
        confidence = 0.5  # Base

        # Volume score (CRITICAL!)
        if volume_ratio >= 5.0:  # HUGE spike
            confidence += 0.20
        elif volume_ratio >= 4.0:  # Very strong
            confidence += 0.15
        elif volume_ratio >= 3.0:  # Strong
            confidence += 0.12
        else:
            confidence += 0.05

        # Consolidation tightness score
        if atr_pct < 1.0:  # Very tight
            confidence += 0.15
        elif atr_pct < 1.5:  # Tight
            confidence += 0.12
        elif atr_pct < 2.0:  # Moderate
            confidence += 0.08
        else:
            confidence += 0.03

        # RSI health score
        rsi_distance = abs(rsi - 50)
        if rsi_distance < 10:  # Very healthy (40-60)
            confidence += 0.15
        elif rsi_distance < 20:  # Healthy (30-70)
            confidence += 0.10
        else:
            confidence += 0.05

        # Breakout strength score
        if breakout_strength > 0.015:  # > 1.5%
            confidence += 0.10
        elif breakout_strength > 0.010:  # > 1.0%
            confidence += 0.08
        else:
            confidence += 0.05

        # False breakout history (important!)
        if no_false_breakouts:
            confidence += 0.10
        else:
            confidence -= 0.10  # Penalty

        return min(max(confidence, 0), 1.0)

    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """
        CARRARMATO Breakout Analysis

        Entry ONLY on confirmed, high-volume breakouts
        """

        if len(df) < self.get_required_candles():
            logger.debug(f"Not enough candles: {len(df)}/{self.get_required_candles()}")
            return None

        # Calculate indicators
        atr = self.calculate_atr(df)
        rsi = self.calculate_rsi(df)
        volume_ratio = self.calculate_volume_profile(df, period=20)

        current_price = df['close'].iloc[-1]
        current_atr = atr.iloc[-1]
        current_rsi = rsi.iloc[-1]

        # ========== FILTER #1: CONSOLIDATION (LOW ATR) ==========
        atr_pct = (current_atr / current_price) * 100

        if atr_pct > self.max_atr_pct:
            logger.debug(f"❌ ATR too high (not consolidating): {atr_pct:.2f}%")
            return None

        logger.debug(f"✅ Consolidation confirmed: ATR={atr_pct:.2f}%")

        # ========== FILTER #2: MASSIVE VOLUME CONFIRMATION ==========
        if volume_ratio < self.volume_multiplier:
            logger.debug(f"❌ Volume too low: {volume_ratio:.2f}x (min {self.volume_multiplier}x)")
            return None

        logger.debug(f"✅ MASSIVE Volume spike: {volume_ratio:.2f}x")

        # ========== FILTER #3: RSI FILTER (NOT EXTREME) ==========
        if current_rsi < self.rsi_min or current_rsi > self.rsi_max:
            logger.debug(f"❌ RSI extreme: {current_rsi:.1f} (need {self.rsi_min}-{self.rsi_max})")
            return None

        logger.debug(f"✅ RSI healthy: {current_rsi:.1f}")

        # ========== FILTER #4: NO FALSE BREAKOUTS ==========
        no_false_breakouts = self.check_false_breakout_history(df)
        if not no_false_breakouts:
            return None

        logger.debug(f"✅ No recent false breakouts")

        # ========== FILTER #5: DETECT BREAKOUT ==========
        breakout = self.detect_breakout(df, period=self.consolidation_period)

        if breakout is None:
            logger.debug(f"❌ No breakout detected")
            return None

        # Calculate support/resistance levels
        recent_high = df['high'].iloc[-(self.consolidation_period+1):-1].max()
        recent_low = df['low'].iloc[-(self.consolidation_period+1):-1].min()

        signal = None

        # ========== UPWARD BREAKOUT ==========
        if breakout == 'UP':
            # Ensure price is ABOVE recent high
            if current_price > recent_high:
                breakout_strength = (current_price - recent_high) / recent_high

                # Calculate confidence
                confidence = self.calculate_signal_confidence(
                    volume_ratio, atr_pct, current_rsi,
                    breakout_strength, no_false_breakouts
                )

                logger.debug(f"   Breakout strength: {breakout_strength*100:.2f}%, Confidence: {confidence:.0%}")

                # Only enter if confidence high enough
                if confidence >= self.min_confidence:
                    entry_price = current_price
                    stop_loss = entry_price * (1 - self.stop_loss_pct)
                    take_profit = entry_price * (1 + self.take_profit_pct)

                    signal = {
                        'action': 'LONG',
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'leverage': self.default_leverage,
                        'confidence': confidence,
                        'reason': f'🛡️ CARRARMATO Breakout UP: Vol={volume_ratio:.1f}x, ' +
                                f'ATR={atr_pct:.2f}%, RSI={current_rsi:.0f}, ' +
                                f'Strength={breakout_strength*100:.1f}%, Conf={confidence:.0%}'
                    }
                    logger.info(f"🎯 HIGH CONFIDENCE LONG BREAKOUT SIGNAL: {confidence:.0%}")
                else:
                    logger.debug(f"⚠️ Confidence too low for LONG: {confidence:.0%} (min {self.min_confidence:.0%})")

        # ========== DOWNWARD BREAKOUT ==========
        elif breakout == 'DOWN':
            # Ensure price is BELOW recent low
            if current_price < recent_low:
                breakout_strength = (recent_low - current_price) / recent_low

                # Calculate confidence
                confidence = self.calculate_signal_confidence(
                    volume_ratio, atr_pct, current_rsi,
                    breakout_strength, no_false_breakouts
                )

                logger.debug(f"   Breakout strength: {breakout_strength*100:.2f}%, Confidence: {confidence:.0%}")

                # Only enter if confidence high enough
                if confidence >= self.min_confidence:
                    entry_price = current_price
                    stop_loss = entry_price * (1 + self.stop_loss_pct)
                    take_profit = entry_price * (1 - self.take_profit_pct)

                    signal = {
                        'action': 'SHORT',
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'leverage': self.default_leverage,
                        'confidence': confidence,
                        'reason': f'🛡️ CARRARMATO Breakout DOWN: Vol={volume_ratio:.1f}x, ' +
                                f'ATR={atr_pct:.2f}%, RSI={current_rsi:.0f}, ' +
                                f'Strength={breakout_strength*100:.1f}%, Conf={confidence:.0%}'
                    }
                    logger.info(f"🎯 HIGH CONFIDENCE SHORT BREAKOUT SIGNAL: {confidence:.0%}")
                else:
                    logger.debug(f"⚠️ Confidence too low for SHORT: {confidence:.0%} (min {self.min_confidence:.0%})")

        if signal and self.validate_signal(signal):
            logger.info(f"[{self.name}] 🛡️ CARRARMATO SIGNAL: {signal['action']} for {symbol}")
            logger.info(f"   Entry: ${signal['entry_price']:.2f}, SL: ${signal['stop_loss']:.2f}, TP: ${signal['take_profit']:.2f}")
            logger.info(f"   R/R: 1:{self.take_profit_pct/self.stop_loss_pct:.1f}, Confidence: {signal['confidence']:.0%}")
            return signal

        return None
