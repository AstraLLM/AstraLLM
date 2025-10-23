#!/usr/bin/env python3
"""
Script per creare le nuove tabelle nel database
Esegui questo PRIMA di riavviare il bot
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.bot_state import BotStateManager
from loguru import logger

def main():
    """Create database tables"""

    logger.info("🔧 Creazione tabelle database...")

    try:
        # Initialize database manager (this creates all tables)
        db_manager = BotStateManager("data/bot_state.db")

        logger.info("✅ Tabelle create con successo!")
        logger.info("")
        logger.info("Tabelle disponibili:")
        logger.info("  1. bot_state (già esistente)")
        logger.info("  2. trades (NUOVA)")
        logger.info("  3. positions_history (NUOVA)")
        logger.info("  4. market_conditions (NUOVA)")
        logger.info("  5. strategy_performance (NUOVA)")
        logger.info("  6. signals (NUOVA)")
        logger.info("")
        logger.info("🎯 Ora puoi riavviare il bot: docker-compose up -d")

        return True

    except Exception as e:
        logger.error(f"❌ Errore durante la creazione delle tabelle: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
