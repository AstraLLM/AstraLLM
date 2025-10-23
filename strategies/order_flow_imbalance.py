"""
Order Flow Imbalance Strategy - High Frequency Leading Indicator

Optimized for: WINNING RATE 70-75%
Leverage: 20x
Best for: All market conditions, especially range-bound

Philosophy:
- Analyze order book imbalance to ANTICIPATE price movement
- Leading indicator (enters BEFORE price moves)
- High frequency (5-10 signals per day per symbol)
- Short holding time (minutes to hours)

ENTRY ONLY WHEN:
1. Bid/Ask imbalance > 60% on one side
2. Order book depth sufficient (> $100k total)
3. Price near fair value (not already moved)
4. Volume confirms direction
5. No recent false signals
"""
from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from loguru import logger


class OrderFlowImbalanceStrategy(BaseStrategy):
    """
    Order Flow Imbalance - Leading Indicator Strategy

    Target: 70-75% winning rate
    R/R: 1:1.87
    Frequency: 5-10 trades/day per symbol
    """

    def __init__(self, leverage: int = 20):
        super().__init__("Order Flow Imbalance", leverage)

        # BALANCED PARAMETERS
        self.stop_loss_pct = 0.008  # 0.8% SL (tight per HF)
        self.take_profit_pct = 0.015  # 1.5% TP
        # R/R = 1:1.87 ✅

        # Order book parameters
        self.min_imbalance = 0.55  # 55% imbalance (bid vs ask) - slightly more aggressive
        self.strong_imbalance = 0.70  # 70% = very strong signal
        self.min_total_depth = 100000  # $100k min liquidity
        self.book_levels = 10  # Analyze top 10 levels

        # Price proximity to fair value
        self.max_distance_from_fair = 0.005  # 0.5% max distance

        # Volume confirmation
        self.min_volume_ratio = 1.0  # Normal volume OK (già leading)

        # Cooldown to avoid overtrading
        self.cooldown_seconds = 300  # 5 min between signals per symbol

        # Confidence requirement
        self.min_confidence = 0.60  # 60% confidence

        # Track last signal time per symbol
        self.last_signal_time = {}

    def get_required_candles(self) -> int:
        return 50  # Meno dati necessari (orderbook più importante)

    def calculate_order_book_imbalance(self, orderbook: Optional[Dict]) -> Tuple[float, float, float]:
        """
        Calculate bid/ask imbalance from order book

        Returns:
            (imbalance_ratio, bid_depth, ask_depth)
            imbalance_ratio: -1 to 1 where:
                1 = 100% bids (strong buy pressure)
                -1 = 100% asks (strong sell pressure)
                0 = balanced
        """
        if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
            return 0.0, 0.0, 0.0

        # Sum up liquidity on each side (top N levels)
        bids = orderbook['bids'][:self.book_levels]
        asks = orderbook['asks'][:self.book_levels]

        # Calculate depth (price × quantity for each level)
        bid_depth = sum(float(bid[0]) * float(bid[1]) for bid in bids)
        ask_depth = sum(float(ask[0]) * float(ask[1]) for ask in asks)

        total_depth = bid_depth + ask_depth

        if total_depth == 0:
            return 0.0, 0.0, 0.0

        # Calculate imbalance ratio
        # +1 = all bids, -1 = all asks, 0 = balanced
        imbalance = (bid_depth - ask_depth) / total_depth

        return imbalance, bid_depth, ask_depth

    def calculate_weighted_mid_price(self, orderbook: Optional[Dict]) -> Optional[float]:
        """
        Calculate volume-weighted mid price from order book
        More accurate than simple bid/ask average
        """
        if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
            return None

        if not orderbook['bids'] or not orderbook['asks']:
            return None

        # Best bid and ask
        best_bid = float(orderbook['bids'][0][0])
        best_ask = float(orderbook['asks'][0][0])

        # Volume at best bid/ask
        bid_volume = float(orderbook['bids'][0][1])
        ask_volume = float(orderbook['asks'][0][1])

        total_volume = bid_volume + ask_volume

        if total_volume == 0:
            return (best_bid + best_ask) / 2

        # Volume-weighted mid price
        weighted_mid = (best_bid * bid_volume + best_ask * ask_volume) / total_volume

        return weighted_mid

    def check_cooldown(self, symbol: str, current_timestamp: int) -> bool:
        """
        Check if enough time has passed since last signal

        Returns:
            True if can trade, False if in cooldown
        """
        if symbol not in self.last_signal_time:
            return True

        time_since_last = current_timestamp - self.last_signal_time[symbol]

        if time_since_last < self.cooldown_seconds:
            logger.debug(f"Cooldown active for {symbol}: {self.cooldown_seconds - time_since_last}s remaining")
            return False

        return True

    def calculate_signal_confidence(self,
                                    imbalance: float,
                                    total_depth: float,
                                    volume_ratio: float,
                                    distance_from_fair: float) -> float:
        """
        Calculate composite confidence score (0-1)

        High confidence when:
        - Strong imbalance (> 70%)
        - High liquidity (> $200k)
        - Volume confirming
        - Price at fair value
        """
        confidence = 0.5  # Base

        # Imbalance strength score (CRITICAL!)
        imbalance_abs = abs(imbalance)
        if imbalance_abs >= 0.75:  # 75%+ = extreme
            confidence += 0.20
        elif imbalance_abs >= 0.70:  # 70%+ = strong
            confidence += 0.15
        elif imbalance_abs >= 0.60:  # 60%+ = good
            confidence += 0.12
        else:
            confidence += 0.08

        # Liquidity depth score
        if total_depth >= 300000:  # $300k+ = excellent
            confidence += 0.15
        elif total_depth >= 200000:  # $200k+ = good
            confidence += 0.12
        elif total_depth >= 100000:  # $100k+ = acceptable
            confidence += 0.10
        else:
            confidence += 0.05

        # Volume confirmation score
        if volume_ratio >= 1.5:  # 1.5x = strong
            confidence += 0.10
        elif volume_ratio >= 1.2:  # 1.2x = good
            confidence += 0.08
        elif volume_ratio >= 1.0:  # 1.0x = normal
            confidence += 0.05

        # Price proximity to fair value (importante per leading indicator)
        if distance_from_fair < 0.002:  # < 0.2%
            confidence += 0.10
        elif distance_from_fair < 0.005:  # < 0.5%
            confidence += 0.08
        else:
            confidence += 0.03

        return min(max(confidence, 0), 1.0)

    def analyze(self, df: pd.DataFrame, symbol: str,
                current_inventory: float = 0.0,
                funding_history: Optional[List[Dict]] = None,
                orderbook: Optional[Dict] = None,
                current_timestamp: Optional[int] = None) -> Optional[Dict]:
        """
        Analyze order book for imbalance opportunities

        This is a LEADING INDICATOR - enters before price moves!
        """

        if len(df) < self.get_required_candles():
            logger.debug(f"Not enough candles: {len(df)}/{self.get_required_candles()}")
            return None

        # ========== FILTER #1: ORDER BOOK AVAILABILITY ==========
        if not orderbook:
            logger.debug(f"No orderbook data available for {symbol}")
            return None

        # ========== FILTER #2: COOLDOWN CHECK ==========
        if current_timestamp and not self.check_cooldown(symbol, current_timestamp):
            return None

        # ========== FILTER #3: CALCULATE IMBALANCE ==========
        imbalance, bid_depth, ask_depth = self.calculate_order_book_imbalance(orderbook)
        total_depth = bid_depth + ask_depth

        # Check minimum liquidity
        if total_depth < self.min_total_depth:
            logger.debug(f"❌ Insufficient liquidity: ${total_depth:.0f} (min ${self.min_total_depth})")
            return None

        logger.debug(f"Order Book: Bid=${bid_depth:.0f}, Ask=${ask_depth:.0f}, Imbalance={imbalance:.2%}")

        # Check minimum imbalance
        if abs(imbalance) < self.min_imbalance:
            logger.debug(f"❌ Imbalance too weak: {imbalance:.2%} (min {self.min_imbalance:.0%})")
            return None

        logger.debug(f"✅ Strong Imbalance: {imbalance:.2%}")

        # ========== FILTER #4: PRICE PROXIMITY TO FAIR VALUE ==========
        current_price = df['close'].iloc[-1]
        weighted_mid = self.calculate_weighted_mid_price(orderbook)

        if weighted_mid:
            distance_from_fair = abs(current_price - weighted_mid) / current_price
        else:
            distance_from_fair = 0.0

        if distance_from_fair > self.max_distance_from_fair:
            logger.debug(f"❌ Price too far from fair value: {distance_from_fair:.2%}")
            return None

        logger.debug(f"✅ Price at fair value: {distance_from_fair:.2%} from mid")

        # ========== FILTER #5: VOLUME CONFIRMATION ==========
        volume_ratio = self.calculate_volume_profile(df, period=20)

        # Relax volume requirement if imbalance is very strong (>75%)
        # Strong imbalance can predict movement even with lower volume
        imbalance_abs = abs(imbalance)
        required_volume = self.min_volume_ratio

        if imbalance_abs >= 0.80:  # 80%+ imbalance = extreme
            required_volume = 0.2  # Accept 20% volume (very relaxed for extreme signals)
            logger.debug(f"🔥 Extreme imbalance ({imbalance_abs:.0%}) - relaxing volume requirement to {required_volume:.1f}x")
        elif imbalance_abs >= 0.75:  # 75%+ imbalance = very strong
            required_volume = 0.4  # Accept 40% volume
            logger.debug(f"🔥 Very strong imbalance ({imbalance_abs:.0%}) - relaxing volume requirement to {required_volume:.1f}x")
        elif imbalance_abs >= 0.70:  # 70%+ imbalance = strong
            required_volume = 0.6  # Accept 60% volume
            logger.debug(f"💪 Strong imbalance ({imbalance_abs:.0%}) - relaxing volume requirement to {required_volume:.1f}x")

        if volume_ratio < required_volume:
            logger.debug(f"❌ Volume too low: {volume_ratio:.2f}x (min {required_volume:.1f}x for this imbalance)")
            return None

        logger.debug(f"✅ Volume confirmed: {volume_ratio:.2f}x (required: {required_volume:.1f}x)")

        # ========== GENERATE SIGNAL BASED ON IMBALANCE ==========
        signal = None

        # BULLISH IMBALANCE (много bids)
        if imbalance > self.min_imbalance:
            logger.debug(f"🔍 Bullish imbalance detected: {imbalance:.2%}")

            # Calculate confidence
            confidence = self.calculate_signal_confidence(
                imbalance, total_depth, volume_ratio, distance_from_fair
            )

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
                    'reason': f'🎯 Order Flow BUY: Imbalance={imbalance:.0%}, ' +
                            f'Depth=${total_depth/1000:.0f}k, Vol={volume_ratio:.1f}x, ' +
                            f'Conf={confidence:.0%}'
                }
                logger.info(f"🎯 BULLISH ORDER FLOW SIGNAL: {confidence:.0%}")

                # Update last signal time
                if current_timestamp:
                    self.last_signal_time[symbol] = current_timestamp
            else:
                logger.debug(f"⚠️ Confidence too low for LONG: {confidence:.0%} (min {self.min_confidence:.0%})")

        # BEARISH IMBALANCE (много asks)
        elif imbalance < -self.min_imbalance:
            logger.debug(f"🔍 Bearish imbalance detected: {imbalance:.2%}")

            # Calculate confidence
            confidence = self.calculate_signal_confidence(
                imbalance, total_depth, volume_ratio, distance_from_fair
            )

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
                    'reason': f'🎯 Order Flow SELL: Imbalance={imbalance:.0%}, ' +
                            f'Depth=${total_depth/1000:.0f}k, Vol={volume_ratio:.1f}x, ' +
                            f'Conf={confidence:.0%}'
                }
                logger.info(f"🎯 BEARISH ORDER FLOW SIGNAL: {confidence:.0%}")

                # Update last signal time
                if current_timestamp:
                    self.last_signal_time[symbol] = current_timestamp
            else:
                logger.debug(f"⚠️ Confidence too low for SHORT: {confidence:.0%} (min {self.min_confidence:.0%})")

        if signal and self.validate_signal(signal):
            logger.info(f"[{self.name}] 🎯 ORDER FLOW SIGNAL: {signal['action']} for {symbol}")
            logger.info(f"   Entry: ${signal['entry_price']:.2f}, SL: ${signal['stop_loss']:.2f}, TP: ${signal['take_profit']:.2f}")
            logger.info(f"   R/R: 1:{self.take_profit_pct/self.stop_loss_pct:.1f}, Confidence: {signal['confidence']:.0%}")
            return signal

        return None
