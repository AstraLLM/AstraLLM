"""
Market Regime Detection System

Identifica la fase di mercato in tempo reale combinando:
- Forward-looking indicators (order book, funding trends)
- Volatility regime analysis
- Market microstructure
- Cross-asset correlation

Goal: Selezionare la strategia ottimale PRIMA che il regime cambi completamente
"""
from typing import Dict, List, Optional, Tuple
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger
from dataclasses import dataclass


class MarketRegime(Enum):
    """Market regime types"""
    HIGH_VOLATILITY_TRENDING = "high_vol_trending"
    LOW_VOLATILITY_RANGING = "low_vol_ranging"
    MOMENTUM_EXHAUSTION = "momentum_exhaustion"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class RegimeSignals:
    """Signals used for regime detection"""
    volatility: float  # Current volatility (0-1 normalized)
    trend_strength: float  # ADX-like measure (0-100)
    volume_trend: float  # Volume increasing/decreasing (-1 to 1)
    orderbook_imbalance: float  # Bid/Ask pressure (-1 to 1)
    funding_rate: float  # Current funding rate
    funding_trend: float  # Funding rate trend (-1 to 1)
    rsi: float  # RSI (0-100)
    price_momentum: float  # Rate of change (-1 to 1)
    liquidity_score: float  # Market depth/spread (0-1)
    regime_persistence: float  # How long in current regime (0-1)


class MarketRegimeDetector:
    """
    Detect market regime using multi-factor analysis
    """

    def __init__(self):
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_confidence = 0.0
        self.regime_history: List[Tuple[int, MarketRegime, float]] = []
        self.regime_start_time = None

        # Thresholds for regime classification
        self.volatility_high = 0.03  # 3%
        self.volatility_low = 0.015  # 1.5%
        self.trend_strong = 40  # ADX-like
        self.momentum_extreme_rsi = (25, 75)

        logger.info("Market Regime Detector initialized")

    def calculate_trend_strength(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate trend strength (ADX-like indicator)

        Returns:
            0-100, where 0 = no trend, 100 = very strong trend
        """
        if len(df) < period + 1:
            return 0.0

        # Calculate directional movement
        high = df['high']
        low = df['low']

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        # True range
        tr1 = high - low
        tr2 = abs(high - df['close'].shift())
        tr3 = abs(low - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Smooth
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0.0

    def calculate_orderbook_imbalance(self, orderbook: Optional[Dict]) -> float:
        """
        Calculate order book imbalance

        Args:
            orderbook: Dict with 'bids' and 'asks' (list of [price, size])

        Returns:
            -1 to 1, where -1 = heavy sell pressure, 1 = heavy buy pressure
        """
        if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
            return 0.0

        # Sum up liquidity on each side (top 10 levels)
        bid_liquidity = sum(float(bid[1]) for bid in orderbook['bids'][:10])
        ask_liquidity = sum(float(ask[1]) for ask in orderbook['asks'][:10])

        total_liquidity = bid_liquidity + ask_liquidity

        if total_liquidity == 0:
            return 0.0

        # Imbalance: positive = more bids (bullish), negative = more asks (bearish)
        imbalance = (bid_liquidity - ask_liquidity) / total_liquidity

        return imbalance

    def calculate_funding_trend(self, funding_history: List[Dict]) -> Tuple[float, float]:
        """
        Calculate funding rate and its trend

        Returns:
            (current_funding, trend)
            trend: -1 to 1, where -1 = decreasing fast, 1 = increasing fast
        """
        if not funding_history or len(funding_history) < 2:
            return 0.0, 0.0

        # Get recent funding rates
        rates = [float(f.get('fundingRate', 0)) for f in funding_history[-10:]]
        current_funding = rates[-1]

        # Calculate trend using linear regression
        if len(rates) >= 3:
            x = np.arange(len(rates))
            slope, _ = np.polyfit(x, rates, 1)
            # Normalize slope to -1 to 1 range
            trend = np.clip(slope * 1000, -1, 1)  # Scale factor
        else:
            trend = 0.0

        return current_funding, trend

    def calculate_liquidity_score(self, df: pd.DataFrame, orderbook: Optional[Dict]) -> float:
        """
        Calculate overall market liquidity score

        Factors:
        - Bid/Ask spread
        - Order book depth
        - Recent volume

        Returns:
            0-1, where 0 = illiquid, 1 = very liquid
        """
        score = 0.5  # Default neutral

        # Factor 1: Volume trend
        if len(df) >= 20:
            recent_volume = df['volume'].iloc[-5:].mean()
            avg_volume = df['volume'].iloc[-20:].mean()

            if avg_volume > 0:
                volume_ratio = recent_volume / avg_volume
                score += np.clip((volume_ratio - 1) * 0.2, -0.3, 0.3)

        # Factor 2: Order book depth
        if orderbook:
            bid_depth = sum(float(bid[1]) for bid in orderbook['bids'][:10])
            ask_depth = sum(float(ask[1]) for ask in orderbook['asks'][:10])

            # Normalize (arbitrary scale, adjust based on asset)
            total_depth = bid_depth + ask_depth
            if total_depth > 100000:  # High liquidity threshold
                score += 0.2
            elif total_depth < 10000:  # Low liquidity threshold
                score -= 0.2

        return np.clip(score, 0, 1)

    def calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """Calculate realized volatility"""
        if len(df) < period:
            return 0.0

        returns = df['close'].pct_change()
        volatility = returns.rolling(window=period).std().iloc[-1]

        return volatility if not pd.isna(volatility) else 0.0

    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate RSI"""
        if len(df) < period + 1:
            return 50.0

        close = df['close']
        delta = close.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0

    def calculate_price_momentum(self, df: pd.DataFrame, period: int = 10) -> float:
        """
        Calculate price momentum

        Returns:
            -1 to 1, normalized rate of change
        """
        if len(df) < period + 1:
            return 0.0

        roc = (df['close'].iloc[-1] - df['close'].iloc[-period]) / df['close'].iloc[-period]

        # Normalize to -1 to 1 (assuming max 10% move)
        return np.clip(roc * 10, -1, 1)

    def calculate_volume_trend(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate volume trend

        Returns:
            -1 to 1, where -1 = volume decreasing, 1 = volume increasing
        """
        if len(df) < period + 5:
            return 0.0

        recent_volume = df['volume'].iloc[-5:].mean()
        older_volume = df['volume'].iloc[-(period+5):-5].mean()

        if older_volume == 0:
            return 0.0

        ratio = (recent_volume - older_volume) / older_volume

        # Normalize to -1 to 1
        return np.clip(ratio, -1, 1)

    def extract_signals(self, df: pd.DataFrame,
                       orderbook: Optional[Dict] = None,
                       funding_history: Optional[List[Dict]] = None) -> RegimeSignals:
        """Extract all signals for regime detection"""

        volatility = self.calculate_volatility(df)
        trend_strength = self.calculate_trend_strength(df)
        volume_trend = self.calculate_volume_trend(df)
        orderbook_imbalance = self.calculate_orderbook_imbalance(orderbook)

        funding_rate, funding_trend = self.calculate_funding_trend(funding_history)

        rsi = self.calculate_rsi(df)
        price_momentum = self.calculate_price_momentum(df)
        liquidity_score = self.calculate_liquidity_score(df, orderbook)

        # Regime persistence (how long we've been in current regime)
        regime_persistence = len([r for r in self.regime_history[-20:]
                                 if r[1] == self.current_regime]) / 20.0 if self.regime_history else 0.0

        return RegimeSignals(
            volatility=volatility,
            trend_strength=trend_strength,
            volume_trend=volume_trend,
            orderbook_imbalance=orderbook_imbalance,
            funding_rate=funding_rate,
            funding_trend=funding_trend,
            rsi=rsi,
            price_momentum=price_momentum,
            liquidity_score=liquidity_score,
            regime_persistence=regime_persistence
        )

    def detect_regime(self, signals: RegimeSignals) -> Tuple[MarketRegime, float]:
        """
        Detect market regime from signals

        Returns:
            (regime, confidence)
        """

        scores = {
            MarketRegime.HIGH_VOLATILITY_TRENDING: 0.0,
            MarketRegime.LOW_VOLATILITY_RANGING: 0.0,
            MarketRegime.MOMENTUM_EXHAUSTION: 0.0,
            MarketRegime.MIXED: 0.5  # Default baseline
        }

        # HIGH VOLATILITY TRENDING signals
        if signals.volatility > self.volatility_high:
            scores[MarketRegime.HIGH_VOLATILITY_TRENDING] += 3.0

        if signals.trend_strength > self.trend_strong:
            scores[MarketRegime.HIGH_VOLATILITY_TRENDING] += 2.5

        if abs(signals.price_momentum) > 0.5:
            scores[MarketRegime.HIGH_VOLATILITY_TRENDING] += 2.0

        if signals.volume_trend > 0.3:
            scores[MarketRegime.HIGH_VOLATILITY_TRENDING] += 1.5

        # LOW VOLATILITY RANGING signals
        if signals.volatility < self.volatility_low:
            scores[MarketRegime.LOW_VOLATILITY_RANGING] += 3.0

        if signals.trend_strength < 25:
            scores[MarketRegime.LOW_VOLATILITY_RANGING] += 2.5

        if abs(signals.price_momentum) < 0.2:
            scores[MarketRegime.LOW_VOLATILITY_RANGING] += 2.0

        if abs(signals.funding_rate) > 0.001:  # High funding in low vol = arb opportunity
            scores[MarketRegime.LOW_VOLATILITY_RANGING] += 1.5

        if signals.liquidity_score > 0.7:
            scores[MarketRegime.LOW_VOLATILITY_RANGING] += 1.0

        # MOMENTUM EXHAUSTION signals
        if signals.rsi < self.momentum_extreme_rsi[0] or signals.rsi > self.momentum_extreme_rsi[1]:
            scores[MarketRegime.MOMENTUM_EXHAUSTION] += 3.0

        # Price divergence: strong momentum but weakening volume
        if abs(signals.price_momentum) > 0.4 and signals.volume_trend < -0.2:
            scores[MarketRegime.MOMENTUM_EXHAUSTION] += 2.5

        # Funding rate divergence
        if abs(signals.funding_rate) > 0.002:  # Extreme funding
            scores[MarketRegime.MOMENTUM_EXHAUSTION] += 2.0

        # Order book imbalance extreme (potential reversal)
        if abs(signals.orderbook_imbalance) > 0.6:
            scores[MarketRegime.MOMENTUM_EXHAUSTION] += 1.5

        # Find regime with highest score
        best_regime = max(scores.items(), key=lambda x: x[1])
        regime = best_regime[0]

        # Calculate confidence (0-1)
        total_score = sum(scores.values())
        confidence = best_regime[1] / total_score if total_score > 0 else 0.5

        # Boost confidence if regime persists
        if regime == self.current_regime and signals.regime_persistence > 0.6:
            confidence = min(1.0, confidence * 1.1)

        return regime, confidence

    def update_regime(self, df: pd.DataFrame,
                     orderbook: Optional[Dict] = None,
                     funding_history: Optional[List[Dict]] = None,
                     timestamp: Optional[int] = None) -> Tuple[MarketRegime, float]:
        """
        Update current market regime

        Returns:
            (regime, confidence)
        """

        # Extract signals
        signals = self.extract_signals(df, orderbook, funding_history)

        # Detect regime
        new_regime, confidence = self.detect_regime(signals)

        # Check for regime change
        if new_regime != self.current_regime:
            logger.info(f"🔄 Market Regime Change: {self.current_regime.value} -> {new_regime.value} (confidence: {confidence:.2f})")
            logger.info(f"   Volatility: {signals.volatility*100:.2f}%, Trend: {signals.trend_strength:.1f}, RSI: {signals.rsi:.1f}")

            self.current_regime = new_regime
            self.regime_start_time = timestamp

        # Update history
        if timestamp:
            self.regime_history.append((timestamp, new_regime, confidence))

            # Keep only recent history
            if len(self.regime_history) > 1000:
                self.regime_history = self.regime_history[-1000:]

        self.regime_confidence = confidence

        return new_regime, confidence

    def get_regime_stats(self) -> Dict:
        """Get statistics about regime history"""
        if not self.regime_history:
            return {}

        # Count regimes
        regime_counts = {}
        for _, regime, _ in self.regime_history[-100:]:  # Last 100 updates
            regime_counts[regime.value] = regime_counts.get(regime.value, 0) + 1

        return {
            'current_regime': self.current_regime.value,
            'confidence': self.regime_confidence,
            'regime_distribution': regime_counts,
            'total_updates': len(self.regime_history)
        }

    def get_recommended_strategies(self, regime: Optional[MarketRegime] = None) -> List[str]:
        """
        Get recommended strategies for current or specified regime

        Returns:
            List of strategy names in priority order
        """
        if regime is None:
            regime = self.current_regime

        strategy_map = {
            MarketRegime.HIGH_VOLATILITY_TRENDING: [
                "Breakout Scalping",
                "Momentum Reversal",
                "Support/Resistance Bounce",
                "Order Flow Imbalance"
            ],
            MarketRegime.LOW_VOLATILITY_RANGING: [
                "Market Making",
                "VWAP Reversion",
                "Order Flow Imbalance",
                "Support/Resistance Bounce"
            ],
            MarketRegime.MOMENTUM_EXHAUSTION: [
                "Momentum Reversal",
                "VWAP Reversion",
                "Support/Resistance Bounce",
                "Order Flow Imbalance"
            ],
            MarketRegime.MIXED: [
                "Order Flow Imbalance",
                "VWAP Reversion",
                "Breakout Scalping",
                "Market Making",
                "Momentum Reversal",
                "Support/Resistance Bounce"
            ],
            MarketRegime.UNKNOWN: [
                "Order Flow Imbalance",
                "VWAP Reversion",
                "Support/Resistance Bounce"
            ]
        }

        return strategy_map.get(regime, strategy_map[MarketRegime.MIXED])
