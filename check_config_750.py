"""
Quick Configuration Check for $750 Setup

Verifica che tutto sia configurato correttamente prima di avviare il bot
"""
from loguru import logger
import sys
import os

def check_env_file():
    """Check if .env file exists and has required fields"""
    logger.info("🔍 Checking .env file...")

    env_path = "config/.env"
    if not os.path.exists(env_path):
        logger.error("❌ File config/.env NON trovato!")
        logger.error("   Crea il file copiando config/.env.example")
        return False

    logger.success("✅ File .env trovato")

    # Check required fields
    with open(env_path, 'r') as f:
        content = f.read()

    required_fields = {
        'ASTER_API_WALLET_ADDRESS': False,
        'ASTER_USER_WALLET_ADDRESS': False,
        'ASTER_PRIVATE_KEY': False,
        'BACKTEST_INITIAL_CAPITAL': False,
        'DEFAULT_LEVERAGE': False,
        'RISK_PER_TRADE': False
    }

    for field in required_fields.keys():
        if field in content:
            required_fields[field] = True

    all_found = all(required_fields.values())

    if all_found:
        logger.success("✅ Tutti i campi richiesti presenti")
    else:
        logger.warning("⚠️ Alcuni campi mancanti:")
        for field, found in required_fields.items():
            if not found:
                logger.warning(f"   - {field}")

    # Check if default values still present
    placeholders = [
        'your_api_wallet_address_here',
        'your_user_wallet_address_here',
        'your_private_key_here'
    ]

    has_placeholders = any(p in content for p in placeholders)

    if has_placeholders:
        logger.error("❌ CREDENZIALI NON CONFIGURATE!")
        logger.error("   Devi sostituire i placeholder in config/.env con le tue credenziali reali")
        logger.error("   Cerca: 'your_api_wallet_address_here' e sostituisci")
        return False

    logger.success("✅ Credenziali configurate")
    return True


def check_config_values():
    """Check that config values match $750 setup"""
    logger.info("\n🔍 Checking configuration values...")

    try:
        from config import get_settings
        settings = get_settings()

        # Expected values for $750 setup
        checks = {
            'Capital': (settings.backtest_initial_capital, 750, "BACKTEST_INITIAL_CAPITAL"),
            'Default Leverage': (settings.default_leverage, 20, "DEFAULT_LEVERAGE"),
            'Max Leverage': (settings.max_leverage, 30, "MAX_LEVERAGE"),
            'Risk per Trade': (settings.risk_per_trade, 0.015, "RISK_PER_TRADE"),
            'Max Daily Loss': (settings.max_daily_loss, 0.08, "MAX_DAILY_LOSS"),
            'Max Open Positions': (settings.max_open_positions, 2, "MAX_OPEN_POSITIONS")
        }

        all_correct = True

        for name, (actual, expected, var_name) in checks.items():
            if actual == expected:
                logger.success(f"✅ {name}: {actual}")
            else:
                logger.warning(f"⚠️ {name}: {actual} (raccomandato: {expected})")
                logger.warning(f"   Modifica {var_name} in config/.env")
                all_correct = False

        # Check strategies
        logger.info("\n🎯 Strategie abilitate:")
        strategies = {
            'Breakout Scalping': settings.enable_breakout_scalping,
            'Momentum Reversal': settings.enable_momentum_reversal,
            'Funding Arbitrage': settings.enable_funding_arbitrage,
            'Liquidation Cascade': settings.enable_liquidation_cascade,
            'Market Making': settings.enable_market_making
        }

        for name, enabled in strategies.items():
            status = "✅ ON" if enabled else "❌ OFF"
            logger.info(f"   {name}: {status}")

        if settings.enable_liquidation_cascade:
            logger.warning("⚠️ Liquidation Cascade è abilitata!")
            logger.warning("   È molto rischiosa (leva 45x). Consigliato disabilitarla per iniziare.")

        return all_correct

    except Exception as e:
        logger.error(f"❌ Errore loading config: {e}")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    logger.info("\n🔍 Checking dependencies...")

    required_packages = [
        'pandas',
        'numpy',
        'loguru',
        'fastapi',
        'uvicorn',
        'web3',
        'requests'
    ]

    missing = []

    for package in required_packages:
        try:
            __import__(package)
            logger.success(f"✅ {package}")
        except ImportError:
            logger.error(f"❌ {package} NOT installed")
            missing.append(package)

    if missing:
        logger.error("\n❌ Pacchetti mancanti!")
        logger.error("   Installa con: pip install -r requirements.txt")
        return False

    logger.success("✅ Tutte le dipendenze installate")
    return True


def calculate_risk_metrics():
    """Calculate and display risk metrics for $750"""
    logger.info("\n📊 Risk Metrics con $750:")

    try:
        from config import get_settings
        settings = get_settings()

        capital = settings.backtest_initial_capital
        risk_per_trade = settings.risk_per_trade
        max_daily_loss = settings.max_daily_loss
        max_positions = settings.max_open_positions
        leverage = settings.default_leverage

        risk_amount = capital * risk_per_trade
        max_loss = capital * max_daily_loss
        max_risk_concurrent = risk_amount * max_positions
        notional_per_trade = capital * leverage

        logger.info(f"   Capital iniziale: ${capital:.2f}")
        logger.info(f"   Risk per trade: ${risk_amount:.2f} ({risk_per_trade*100}%)")
        logger.info(f"   Max loss giornaliero: ${max_loss:.2f} ({max_daily_loss*100}%)")
        logger.info(f"   Max risk con {max_positions} posizioni: ${max_risk_concurrent:.2f}")
        logger.info(f"   Notional per trade ({leverage}x): ${notional_per_trade:.2f}")
        logger.info(f"   Trades fino a daily stop: ~{int(max_loss / risk_amount)}")

        logger.info("\n💡 Interpretazione:")
        logger.info(f"   - Ogni trade rischi: ${risk_amount:.2f}")
        logger.info(f"   - Target profit per trade: ${risk_amount * 2:.2f} - ${risk_amount * 2.5:.2f}")
        logger.info(f"   - Dopo {int(max_loss / risk_amount)} trade perdenti → bot si ferma")
        logger.info(f"   - Worst case scenario in 1 giorno: -{max_daily_loss*100}% (${max_loss:.2f})")

        # Win rate needed for breakeven
        avg_rr = 2.0  # Average risk/reward
        breakeven_wr = 1 / (1 + avg_rr)
        logger.info(f"\n📈 Con R/R medio {avg_rr}:1")
        logger.info(f"   - Win Rate per break-even: {breakeven_wr*100:.1f}%")
        logger.info(f"   - Win Rate target: 55-60%")

        return True

    except Exception as e:
        logger.error(f"❌ Errore calcolo metrics: {e}")
        return False


def print_next_steps():
    """Print next steps"""
    logger.info("\n" + "="*60)
    logger.info("📋 NEXT STEPS")
    logger.info("="*60)

    logger.info("\n1. ⚠️ Se credenziali NON configurate:")
    logger.info("   - Apri: config/.env")
    logger.info("   - Sostituisci 'your_..._here' con le tue credenziali Aster")

    logger.info("\n2. 🧪 Test in Dry Run mode (OBBLIGATORIO):")
    logger.info("   python start_bot_auto.py")
    logger.info("   Lascia girare 7-10 giorni in paper trading")

    logger.info("\n3. 📊 Monitora la Dashboard:")
    logger.info("   http://localhost:8000")
    logger.info("   Controlla win rate > 55% prima di live trading")

    logger.info("\n4. 💰 Live Trading (solo dopo dry run positivo):")
    logger.info("   - Apri: start_bot_auto.py")
    logger.info("   - Cambia: DRY_RUN = True → DRY_RUN = False")
    logger.info("   - Avvia: python start_bot_auto.py")

    logger.info("\n5. 📱 Monitora 2-3 volte al giorno:")
    logger.info("   - Mattina: Check overnight performance")
    logger.info("   - Sera: Review daily trades")

    logger.info("\n📚 Guide complete:")
    logger.info("   - START_HERE_750.md - Guida completa setup $750")
    logger.info("   - README.md - Documentazione generale")
    logger.info("   - AUTONOMOUS_MODE.md - Come funziona il sistema")


def main():
    """Main check function"""
    logger.remove()
    logger.add(sys.stderr, format="<level>{message}</level>")

    logger.info("="*60)
    logger.info("🔍 ASTER Configuration Check - $750 Setup")
    logger.info("="*60)

    checks = [
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("Configuration Values", check_config_values),
        ("Risk Metrics", calculate_risk_metrics)
    ]

    results = []

    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"❌ Error during {name} check: {e}")
            results.append((name, False))

    # Summary
    logger.info("\n" + "="*60)
    logger.info("📊 SUMMARY")
    logger.info("="*60)

    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {name}")
        if not result:
            all_passed = False

    if all_passed:
        logger.success("\n🎉 Setup completato correttamente!")
        logger.success("Sei pronto per iniziare il dry run testing.")
    else:
        logger.error("\n⚠️ Alcuni check falliti!")
        logger.error("Risolvi i problemi sopra prima di procedere.")

    print_next_steps()

    logger.info("\n" + "="*60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
