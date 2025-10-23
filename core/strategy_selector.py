"""
Dynamic Strategy Selector

Seleziona automaticamente la strategia migliore basandosi su:
- Market regime detection
- Recent strategy performance
- Risk management
"""
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from loguru import logger
from .market_regime import MarketRegimeDetector, MarketRegime


class StrategySelector:
    """
    Dynamically select best trading strategy based on market conditions
    """

    def __init__(self, strategies: List):
        """
        Args:
            strategies: List of strategy instances
        """
        self.strategies = {s.name: s for s in strategies}
        self.regime_detector = MarketRegimeDetector()

        # Track strategy performance
        self.strategy_stats = {name: {
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'recent_trades': [],
            'win_rate': 0.0,
            'avg_pnl': 0.0,
            'enabled': True
        } for name in self.strategies.keys()}

        # Selection parameters
        self.min_confidence = 0.6  # Minimum regime confidence to switch
        self.performance_weight = 0.3  # Weight of past performance in selection
        self.regime_weight = 0.7  # Weight of regime matching in selection

        logger.info(f"Strategy Selector initialized with {len(strategies)} strategies")

    def update_strategy_performance(self, strategy_name: str, pnl: float, win: bool):
        """
        Update strategy performance stats

        Args:
            strategy_name: Name of strategy
            pnl: Profit/Loss from trade
            win: Whether trade was profitable
        """
        if strategy_name not in self.strategy_stats:
            logger.warning(f"Unknown strategy: {strategy_name}")
            return

        stats = self.strategy_stats[strategy_name]

        # Update counts
        if win:
            stats['wins'] += 1
        else:
            stats['losses'] += 1

        stats['total_pnl'] += pnl

        # Track recent trades (last 20)
        stats['recent_trades'].append({'pnl': pnl, 'win': win})
        if len(stats['recent_trades']) > 20:
            stats['recent_trades'] = stats['recent_trades'][-20:]

        # Recalculate metrics
        total_trades = stats['wins'] + stats['losses']
        if total_trades > 0:
            stats['win_rate'] = stats['wins'] / total_trades
            stats['avg_pnl'] = stats['total_pnl'] / total_trades

        # Auto-disable underperforming strategies (after min 10 trades)
        if total_trades >= 10:
            if stats['win_rate'] < 0.35:  # Less than 35% win rate
                logger.warning(f"⚠️ Strategy {strategy_name} performing poorly (WR: {stats['win_rate']:.2%}). Consider disabling.")
                stats['enabled'] = False
            elif stats['win_rate'] > 0.45 and not stats['enabled']:
                # Re-enable if improves
                logger.info(f"✅ Strategy {strategy_name} improved (WR: {stats['win_rate']:.2%}). Re-enabling.")
                stats['enabled'] = True

        logger.debug(f"Updated {strategy_name} stats: WR={stats['win_rate']:.2%}, Avg PnL={stats['avg_pnl']:.2f}")

    def calculate_strategy_score(self, strategy_name: str, regime: MarketRegime,
                                 regime_confidence: float) -> float:
        """
        Calculate composite score for strategy selection

        Returns:
            0-1 score, higher = better fit
        """
        # Get recommended strategies for regime
        recommended = self.regime_detector.get_recommended_strategies(regime)

        # Regime match score
        if strategy_name in recommended:
            regime_score = 1.0 - (recommended.index(strategy_name) * 0.2)  # Higher priority = higher score
        else:
            regime_score = 0.2  # Low but not zero

        # Adjust by regime confidence
        regime_score *= regime_confidence

        # Performance score
        stats = self.strategy_stats[strategy_name]

        if not stats['enabled']:
            return 0.0  # Don't select disabled strategies

        total_trades = stats['wins'] + stats['losses']

        if total_trades == 0:
            # No history - use moderate score
            performance_score = 0.5
        else:
            # Recent performance (last 10 trades)
            recent_trades = stats['recent_trades'][-10:]
            recent_wins = sum(1 for t in recent_trades if t['win'])
            recent_wr = recent_wins / len(recent_trades) if recent_trades else 0.5

            # Recent average PnL
            recent_pnl = np.mean([t['pnl'] for t in recent_trades]) if recent_trades else 0.0

            # Combine win rate and PnL
            performance_score = (recent_wr * 0.6) + (min(recent_pnl / 100, 0.4))  # Cap PnL contribution

        # Weighted combination
        final_score = (regime_score * self.regime_weight) + (performance_score * self.performance_weight)

        return np.clip(final_score, 0, 1)

    def select_strategy(self, df: pd.DataFrame,
                       orderbook: Optional[Dict] = None,
                       funding_history: Optional[List[Dict]] = None,
                       timestamp: Optional[int] = None) -> Optional[Tuple[str, float]]:
        """
        Select best strategy for current market conditions

        Returns:
            (strategy_name, confidence) or None
        """

        # Update market regime
        regime, regime_confidence = self.regime_detector.update_regime(
            df, orderbook, funding_history, timestamp
        )

        # Calculate scores for all strategies
        strategy_scores = {}

        for strategy_name in self.strategies.keys():
            score = self.calculate_strategy_score(strategy_name, regime, regime_confidence)
            strategy_scores[strategy_name] = score

        # Get best strategy
        if not strategy_scores:
            return None

        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])
        strategy_name, confidence = best_strategy

        logger.info(f"📊 Selected Strategy: {strategy_name} (confidence: {confidence:.2%})")
        logger.info(f"   Market Regime: {regime.value} (confidence: {regime_confidence:.2%})")
        logger.info(f"   Strategy Scores: {', '.join([f'{k}: {v:.2f}' for k, v in sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)])}")

        return strategy_name, confidence

    def get_strategy_instance(self, strategy_name: str):
        """Get strategy instance by name"""
        return self.strategies.get(strategy_name)

    def analyze_with_best_strategy(self, df: pd.DataFrame, symbol: str,
                                   orderbook: Optional[Dict] = None,
                                   funding_history: Optional[List[Dict]] = None,
                                   timestamp: Optional[int] = None) -> Optional[Dict]:
        """
        Analyze market with dynamically selected best strategy

        If the best strategy doesn't generate a signal, tries alternatives in order of score

        Returns:
            Signal dict or None
        """

        # Update market regime and get all strategy scores
        regime, regime_confidence = self.regime_detector.update_regime(
            df, orderbook, funding_history, timestamp
        )

        # Calculate scores for all strategies
        strategy_scores = {}
        for strategy_name in self.strategies.keys():
            score = self.calculate_strategy_score(strategy_name, regime, regime_confidence)
            strategy_scores[strategy_name] = score

        # Sort strategies by score (best first)
        sorted_strategies = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)

        if not sorted_strategies:
            logger.warning("No strategies available")
            return None

        # Log all scores
        logger.info(f"📊 Market Regime: {regime.value} (confidence: {regime_confidence:.2%})")
        logger.info(f"   Strategy Scores: {', '.join([f'{k}: {v:.2f}' for k, v in sorted_strategies])}")

        # Try strategies in order of score until one generates a signal
        for strategy_name, confidence in sorted_strategies:
            # Skip if score too low
            if confidence < 0.2:
                logger.debug(f"⏭️ Skipping {strategy_name} (score too low: {confidence:.2f})")
                continue

            # Get strategy instance
            strategy = self.get_strategy_instance(strategy_name)

            if not strategy:
                logger.error(f"Strategy not found: {strategy_name}")
                continue

            logger.debug(f"🔍 Trying {strategy_name} (score: {confidence:.2f})...")

            # Analyze with strategy
            try:
                # Different strategies have different analyze() signatures
                # We need to call them correctly based on their requirements
                signal = None

                if strategy_name == "Funding Arbitrage" and funding_history:
                    # Funding Arbitrage needs funding_history
                    signal = strategy.analyze(df, symbol, funding_history=funding_history)
                elif strategy_name == "Order Flow Imbalance":
                    # Order Flow Imbalance needs orderbook and timestamp
                    signal = strategy.analyze(
                        df, symbol,
                        orderbook=orderbook,
                        current_timestamp=timestamp
                    )
                else:
                    # Most strategies just need df and symbol
                    signal = strategy.analyze(df, symbol)

                if signal:
                    # Add metadata
                    signal['selected_strategy'] = strategy_name
                    signal['selection_confidence'] = confidence
                    signal['market_regime'] = regime.value

                    logger.info(f"✅ Signal from {strategy_name}: {signal['action']} @ {signal['entry_price']}")
                    return signal
                else:
                    logger.debug(f"   No signal from {strategy_name}")

            except Exception as e:
                logger.error(f"Error analyzing with {strategy_name}: {e}")
                continue

        # No strategy generated a signal
        logger.debug("❌ No signals from any strategy")
        return None

    def get_stats(self) -> Dict:
        """Get selector statistics"""
        regime_stats = self.regime_detector.get_regime_stats()

        strategy_summary = {}
        for name, stats in self.strategy_stats.items():
            total = stats['wins'] + stats['losses']
            strategy_summary[name] = {
                'total_trades': total,
                'win_rate': stats['win_rate'],
                'total_pnl': stats['total_pnl'],
                'avg_pnl': stats['avg_pnl'],
                'enabled': stats['enabled']
            }

        return {
            'regime': regime_stats,
            'strategies': strategy_summary
        }

    def print_stats(self):
        """Print formatted statistics"""
        stats = self.get_stats()

        logger.info("=" * 60)
        logger.info("📊 STRATEGY SELECTOR STATISTICS")
        logger.info("=" * 60)

        # Regime stats
        logger.info(f"\n🎯 Current Market Regime: {stats['regime'].get('current_regime', 'unknown')}")
        logger.info(f"   Confidence: {stats['regime'].get('confidence', 0):.2%}")

        if 'regime_distribution' in stats['regime']:
            logger.info("\n   Regime Distribution (last 100 updates):")
            for regime, count in stats['regime']['regime_distribution'].items():
                logger.info(f"   - {regime}: {count}%")

        # Strategy stats
        logger.info("\n📈 Strategy Performance:")
        for name, s_stats in stats['strategies'].items():
            status = "✅ ENABLED" if s_stats['enabled'] else "❌ DISABLED"
            logger.info(f"\n   {name} [{status}]")
            logger.info(f"   - Total Trades: {s_stats['total_trades']}")
            logger.info(f"   - Win Rate: {s_stats['win_rate']:.2%}")
            logger.info(f"   - Total PnL: ${s_stats['total_pnl']:.2f}")
            logger.info(f"   - Avg PnL: ${s_stats['avg_pnl']:.2f}")

        logger.info("=" * 60)
