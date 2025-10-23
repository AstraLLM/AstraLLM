"""
Bot State Manager - Persistent storage for bot state using SQLite

This module handles persistent storage of critical bot state like:
- Initial balance (for accurate PnL calculation across restarts)
- First run timestamp
- Last known balance
"""

import sqlite3
from datetime import datetime
from typing import Optional
from loguru import logger


class BotStateManager:
    """Manages persistent bot state using SQLite"""

    def __init__(self, db_path: str = "data/bot_state.db"):
        """
        Initialize the bot state manager

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create state table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create trades table - TUTTI i trade chiusi
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aster_trade_id TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    leverage INTEGER NOT NULL,
                    pnl REAL NOT NULL,
                    pnl_percentage REAL NOT NULL,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP NOT NULL,
                    hold_duration_seconds INTEGER,
                    stop_loss REAL,
                    take_profit REAL,
                    exit_reason TEXT,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Add aster_trade_id column if it doesn't exist (migration for existing DBs)
            try:
                cursor.execute("ALTER TABLE trades ADD COLUMN aster_trade_id TEXT UNIQUE")
                logger.info("✅ Added aster_trade_id column to trades table")
            except sqlite3.OperationalError:
                # Column already exists
                pass

            # Create positions table - snapshot delle posizioni aperte
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    leverage INTEGER NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    unrealized_pnl REAL,
                    liquidation_price REAL,
                    entry_time TIMESTAMP NOT NULL,
                    confidence REAL,
                    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create market_conditions table - condizioni di mercato quando apriamo/chiudiamo
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_conditions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    volatility REAL,
                    volume_ratio REAL,
                    rsi REAL,
                    trend_strength REAL,
                    trend_direction TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT
                )
            """)

            # Create strategy_performance table - performance aggregate per strategia
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy TEXT NOT NULL,
                    date DATE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    avg_hold_time_seconds INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(strategy, date)
                )
            """)

            # Create signals table - TUTTI i segnali generati (anche quelli non eseguiti)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    leverage INTEGER,
                    confidence REAL,
                    reason TEXT,
                    executed BOOLEAN DEFAULT 0,
                    rejection_reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()
            logger.info(f"✅ Bot state database initialized with analytics tables: {self.db_path}")

        except Exception as e:
            logger.error(f"Error initializing bot state database: {e}")

    def get_initial_balance(self) -> Optional[float]:
        """
        Get the initial balance recorded at first bot run

        Returns:
            Initial balance as float, or None if not set
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM bot_state WHERE key = 'initial_balance'")
            result = cursor.fetchone()

            conn.close()

            if result:
                return float(result[0])
            return None

        except Exception as e:
            logger.error(f"Error reading initial balance from DB: {e}")
            return None

    def set_initial_balance(self, balance: float) -> bool:
        """
        Set the initial balance (should only be called once on first run)

        Args:
            balance: Initial balance to save

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Insert or replace
            cursor.execute("""
                INSERT OR REPLACE INTO bot_state (key, value, updated_at)
                VALUES ('initial_balance', ?, CURRENT_TIMESTAMP)
            """, (str(balance),))

            # Also record first run timestamp
            cursor.execute("""
                INSERT OR IGNORE INTO bot_state (key, value, updated_at)
                VALUES ('first_run_timestamp', ?, CURRENT_TIMESTAMP)
            """, (datetime.now().isoformat(),))

            conn.commit()
            conn.close()

            logger.info(f"✅ Initial balance saved to DB: ${balance:.2f}")
            return True

        except Exception as e:
            logger.error(f"Error saving initial balance to DB: {e}")
            return False

    def get_first_run_timestamp(self) -> Optional[str]:
        """
        Get the timestamp of the first bot run

        Returns:
            ISO format timestamp string, or None if not set
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM bot_state WHERE key = 'first_run_timestamp'")
            result = cursor.fetchone()

            conn.close()

            if result:
                return result[0]
            return None

        except Exception as e:
            logger.error(f"Error reading first run timestamp from DB: {e}")
            return None

    def update_last_balance(self, balance: float) -> bool:
        """
        Update the last known balance

        Args:
            balance: Current balance

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO bot_state (key, value, updated_at)
                VALUES ('last_balance', ?, CURRENT_TIMESTAMP)
            """, (str(balance),))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Error updating last balance in DB: {e}")
            return False

    def get_last_balance(self) -> Optional[float]:
        """
        Get the last known balance

        Returns:
            Last balance as float, or None if not set
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM bot_state WHERE key = 'last_balance'")
            result = cursor.fetchone()

            conn.close()

            if result:
                return float(result[0])
            return None

        except Exception as e:
            logger.error(f"Error reading last balance from DB: {e}")
            return None

    def get_state(self, key: str) -> Optional[str]:
        """
        Get a generic state value from database

        Args:
            key: State key to retrieve

        Returns:
            State value as string, or None if not set
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM bot_state WHERE key = ?", (key,))
            result = cursor.fetchone()

            conn.close()

            if result:
                return result[0]
            return None

        except Exception as e:
            logger.error(f"Error reading state '{key}' from DB: {e}")
            return None

    def set_state(self, key: str, value: str) -> bool:
        """
        Set a generic state value in database

        Args:
            key: State key to set
            value: State value to save

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO bot_state (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, str(value)))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Error setting state '{key}' in DB: {e}")
            return False

    def save_trade(self, trade_data: dict) -> bool:
        """
        Save a completed trade to the database

        Args:
            trade_data: Dictionary with trade information
                Required: symbol, strategy, side, entry_price, exit_price, quantity,
                         leverage, pnl, pnl_percentage, entry_time, exit_time
                Optional: stop_loss, take_profit, exit_reason, confidence, aster_trade_id

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate hold duration
            from datetime import datetime
            if isinstance(trade_data.get('entry_time'), datetime) and isinstance(trade_data.get('exit_time'), datetime):
                hold_duration = (trade_data['exit_time'] - trade_data['entry_time']).total_seconds()
            else:
                hold_duration = None

            cursor.execute("""
                INSERT INTO trades (
                    aster_trade_id, symbol, strategy, side, entry_price, exit_price, quantity,
                    leverage, pnl, pnl_percentage, entry_time, exit_time,
                    hold_duration_seconds, stop_loss, take_profit, exit_reason, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get('aster_trade_id'),
                trade_data['symbol'],
                trade_data['strategy'],
                trade_data['side'],
                trade_data['entry_price'],
                trade_data['exit_price'],
                trade_data['quantity'],
                trade_data['leverage'],
                trade_data['pnl'],
                trade_data['pnl_percentage'],
                trade_data['entry_time'],
                trade_data['exit_time'],
                hold_duration,
                trade_data.get('stop_loss'),
                trade_data.get('take_profit'),
                trade_data.get('exit_reason'),
                trade_data.get('confidence')
            ))

            conn.commit()
            conn.close()

            logger.info(f"✅ Trade saved to DB: {trade_data['strategy']} {trade_data['side']} {trade_data['symbol']} PnL={trade_data['pnl']:.2f}")
            return True

        except sqlite3.IntegrityError as e:
            logger.debug(f"Trade already exists in DB (aster_trade_id={trade_data.get('aster_trade_id')})")
            return False
        except Exception as e:
            logger.error(f"Error saving trade to DB: {e}")
            return False

    def trade_exists(self, aster_trade_id: str) -> bool:
        """
        Check if a trade with given Aster ID already exists in database

        Args:
            aster_trade_id: Aster trade ID to check

        Returns:
            True if exists, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM trades WHERE aster_trade_id = ?", (aster_trade_id,))
            count = cursor.fetchone()[0]

            conn.close()

            return count > 0

        except Exception as e:
            logger.error(f"Error checking trade existence: {e}")
            return False

    def get_all_trades(self, limit: int = None) -> list:
        """
        Get all trades from database

        Args:
            limit: Optional limit on number of trades to return

        Returns:
            List of trade dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if limit:
                cursor.execute("""
                    SELECT aster_trade_id, symbol, strategy, side, entry_price, exit_price,
                           quantity, leverage, pnl, pnl_percentage, entry_time, exit_time,
                           hold_duration_seconds, stop_loss, take_profit, exit_reason, confidence
                    FROM trades
                    ORDER BY exit_time DESC
                    LIMIT ?
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT aster_trade_id, symbol, strategy, side, entry_price, exit_price,
                           quantity, leverage, pnl, pnl_percentage, entry_time, exit_time,
                           hold_duration_seconds, stop_loss, take_profit, exit_reason, confidence
                    FROM trades
                    ORDER BY exit_time DESC
                """)

            rows = cursor.fetchall()
            conn.close()

            trades = []
            for row in rows:
                trades.append({
                    'aster_trade_id': row[0],
                    'symbol': row[1],
                    'strategy': row[2],
                    'side': row[3],
                    'entry_price': row[4],
                    'exit_price': row[5],
                    'quantity': row[6],
                    'leverage': row[7],
                    'pnl': row[8],
                    'pnl_percentage': row[9],
                    'entry_time': row[10],
                    'exit_time': row[11],
                    'hold_duration_seconds': row[12],
                    'stop_loss': row[13],
                    'take_profit': row[14],
                    'exit_reason': row[15],
                    'confidence': row[16]
                })

            return trades

        except Exception as e:
            logger.error(f"Error fetching trades from DB: {e}")
            return []

    def import_trades_from_aster(self, aster_client, available_strategies: list, limit: int = 200) -> dict:
        """
        Import historical trades from Aster exchange and save to database
        Assigns random strategies to historical trades

        Args:
            aster_client: AsterFuturesClient instance
            available_strategies: List of strategy names to randomly assign
            limit: Number of trades to fetch from Aster

        Returns:
            Dictionary with import statistics
        """
        import random

        try:
            logger.info(f"📥 Importing trades from Aster (limit={limit})...")

            # Fetch trades from Aster
            aster_trades = aster_client.get_account_trades(limit=limit)

            stats = {
                'total_fetched': len(aster_trades),
                'imported': 0,
                'duplicates': 0,
                'errors': 0
            }

            for aster_trade in aster_trades:
                try:
                    # Only import closed positions (with realized PnL)
                    realized_pnl = float(aster_trade.get('realizedPnl', 0))
                    if abs(realized_pnl) < 0.01:
                        continue

                    # Generate unique ID
                    aster_trade_id = str(aster_trade.get('id', ''))

                    # Check if already exists
                    if self.trade_exists(aster_trade_id):
                        stats['duplicates'] += 1
                        continue

                    # Assign random strategy
                    strategy = random.choice(available_strategies)

                    # Get trade data
                    symbol = aster_trade.get('symbol')
                    side = aster_trade.get('side')
                    price = float(aster_trade.get('price', 0))
                    qty = float(aster_trade.get('qty', 0))
                    trade_time_ms = int(aster_trade.get('time', 0))
                    trade_time = datetime.fromtimestamp(trade_time_ms / 1000)

                    # Calculate PnL percentage (approximate)
                    # For historical trades we don't have entry price, so we estimate
                    pnl_percentage = 0
                    if price > 0 and qty > 0:
                        # Rough estimate based on realized PnL
                        pnl_percentage = (realized_pnl / (price * qty)) * 100

                    # Create trade data
                    trade_data = {
                        'aster_trade_id': aster_trade_id,
                        'symbol': symbol,
                        'strategy': strategy,
                        'side': side,
                        'entry_price': price,  # We don't have actual entry, use exit
                        'exit_price': price,
                        'quantity': qty,
                        'leverage': 20,  # Default leverage (we don't know actual)
                        'pnl': realized_pnl,
                        'pnl_percentage': pnl_percentage,
                        'entry_time': trade_time,
                        'exit_time': trade_time,
                        'exit_reason': 'historical_import'
                    }

                    # Save to database
                    if self.save_trade(trade_data):
                        stats['imported'] += 1

                except Exception as e:
                    logger.error(f"Error importing trade {aster_trade.get('id')}: {e}")
                    stats['errors'] += 1

            logger.info(f"✅ Import completed: {stats['imported']} new, {stats['duplicates']} duplicates, {stats['errors']} errors")
            return stats

        except Exception as e:
            logger.error(f"Error during Aster trade import: {e}")
            return {'error': str(e)}

    def save_signal(self, signal_data: dict, executed: bool = False, rejection_reason: str = None) -> bool:
        """
        Save a trading signal to the database

        Args:
            signal_data: Signal dictionary from strategy
            executed: Whether the signal was executed
            rejection_reason: Reason why signal was not executed (if applicable)

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO signals (
                    symbol, strategy, action, entry_price, stop_loss, take_profit,
                    leverage, confidence, reason, executed, rejection_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_data.get('symbol'),
                signal_data.get('strategy', 'unknown'),
                signal_data['action'],
                signal_data['entry_price'],
                signal_data.get('stop_loss'),
                signal_data.get('take_profit'),
                signal_data.get('leverage'),
                signal_data.get('confidence'),
                signal_data.get('reason'),
                executed,
                rejection_reason
            ))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Error saving signal to DB: {e}")
            return False

    def save_market_conditions(self, symbol: str, price: float, event_type: str,
                                volatility: float = None, volume_ratio: float = None,
                                rsi: float = None, trend_strength: float = None,
                                trend_direction: str = None) -> bool:
        """
        Save market conditions at a specific event (trade entry/exit)

        Args:
            symbol: Trading symbol
            price: Current price
            event_type: 'entry', 'exit', 'snapshot'
            volatility, volume_ratio, rsi, trend_strength, trend_direction: Market metrics

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO market_conditions (
                    symbol, price, volatility, volume_ratio, rsi,
                    trend_strength, trend_direction, event_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, price, volatility, volume_ratio, rsi,
                trend_strength, trend_direction, event_type
            ))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Error saving market conditions to DB: {e}")
            return False

    def update_strategy_performance(self, strategy: str, trade_pnl: float,
                                     hold_time_seconds: int, is_winner: bool) -> bool:
        """
        Update daily strategy performance statistics

        Args:
            strategy: Strategy name
            trade_pnl: Trade PnL
            hold_time_seconds: Trade hold duration
            is_winner: Whether trade was profitable

        Returns:
            True if successful, False otherwise
        """
        try:
            from datetime import date
            today = date.today()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get current stats
            cursor.execute("""
                SELECT total_trades, winning_trades, losing_trades, total_pnl, avg_hold_time_seconds
                FROM strategy_performance
                WHERE strategy = ? AND date = ?
            """, (strategy, today))

            result = cursor.fetchone()

            if result:
                # Update existing record
                total_trades, winning_trades, losing_trades, total_pnl, avg_hold_time = result
                total_trades += 1
                if is_winner:
                    winning_trades += 1
                else:
                    losing_trades += 1
                total_pnl += trade_pnl

                # Weighted average for hold time
                avg_hold_time = ((avg_hold_time * (total_trades - 1)) + hold_time_seconds) / total_trades
                win_rate = (winning_trades / total_trades) * 100

                cursor.execute("""
                    UPDATE strategy_performance
                    SET total_trades = ?, winning_trades = ?, losing_trades = ?,
                        total_pnl = ?, win_rate = ?, avg_hold_time_seconds = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE strategy = ? AND date = ?
                """, (total_trades, winning_trades, losing_trades, total_pnl, win_rate, avg_hold_time, strategy, today))

            else:
                # Insert new record
                win_rate = 100.0 if is_winner else 0.0

                cursor.execute("""
                    INSERT INTO strategy_performance (
                        strategy, date, total_trades, winning_trades, losing_trades,
                        total_pnl, win_rate, avg_hold_time_seconds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (strategy, today, 1, 1 if is_winner else 0, 0 if is_winner else 1,
                      trade_pnl, win_rate, hold_time_seconds))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Error updating strategy performance in DB: {e}")
            return False
