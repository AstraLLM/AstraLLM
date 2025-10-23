"""
Configuration management for ASTER Trading Bot
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Aster API Configuration (Web3 Ethereum Signature)
    aster_api_key: str = Field(..., env="ASTER_API_KEY")  # API key from Aster dashboard
    aster_api_secret: str = Field(..., env="ASTER_API_SECRET")  # API secret from Aster dashboard
    aster_signer_address: str = Field(..., env="ASTER_SIGNER_ADDRESS")  # Agent wallet address from Aster

    # User Wallet info (required for authentication)
    aster_user_wallet_address: str = Field(..., env="ASTER_USER_WALLET_ADDRESS")
    aster_private_key: str = Field(..., env="ASTER_PRIVATE_KEY")  # User wallet private key

    # API Endpoints
    aster_futures_api: str = "https://fapi.asterdex.com"
    aster_futures_ws: str = "wss://fstream.asterdex.com"
    aster_spot_api: str = "https://sapi.asterdex.com"
    aster_spot_ws: str = "wss://sstream.asterdex.com"

    # Trading Configuration - ULTRA-SAFE MODE (Post-Loss Recovery)
    default_leverage: int = Field(3, env="DEFAULT_LEVERAGE")  # Era 15 - RIDOTTO per sicurezza
    max_leverage: int = Field(5, env="MAX_LEVERAGE")  # Era 30 - RIDOTTO drasticamente
    risk_per_trade: float = Field(0.005, env="RISK_PER_TRADE")  # Era 0.015 - RIDOTTO a 0.5%
    max_daily_loss: float = Field(0.02, env="MAX_DAILY_LOSS")  # Era 0.06 - RIDOTTO a 2%
    max_open_positions: int = Field(2, env="MAX_OPEN_POSITIONS")  # Era 4 - RIDOTTO a 2

    # Strategy Toggles - ULTRA-SAFE MODE (Solo 2 strategie testate)
    enable_breakout_scalping: bool = Field(True, env="ENABLE_BREAKOUT_SCALPING")  # ✅ ATTIVA (con parametri modificati)
    enable_funding_arbitrage: bool = Field(False, env="ENABLE_FUNDING_ARBITRAGE")  # ❌ Disabilitata
    enable_momentum_reversal: bool = Field(False, env="ENABLE_MOMENTUM_REVERSAL")  # ❌ DISABILITATA (troppo difficile)
    enable_liquidation_cascade: bool = Field(False, env="ENABLE_LIQUIDATION_CASCADE")  # ❌ Disabilitata
    enable_market_making: bool = Field(False, env="ENABLE_MARKET_MAKING")  # ❌ DISABILITATA (causa principale perdite)

    # NEW STRATEGIES - Solo VWAP Reversion attiva
    enable_order_flow_imbalance: bool = Field(False, env="ENABLE_ORDER_FLOW_IMBALANCE")  # ❌ DISABILITATA (troppo complessa)
    enable_vwap_reversion: bool = Field(True, env="ENABLE_VWAP_REVERSION")  # ✅ ATTIVA (con leverage 3x)
    enable_support_resistance: bool = Field(False, env="ENABLE_SUPPORT_RESISTANCE")  # ❌ DISABILITATA (troppi falsi segnali)

    # Backtesting Configuration
    backtest_start_date: str = Field("2024-01-01", env="BACKTEST_START_DATE")
    backtest_end_date: str = Field("2024-12-31", env="BACKTEST_END_DATE")
    backtest_initial_capital: float = Field(10000, env="BACKTEST_INITIAL_CAPITAL")

    # API Configuration
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_secret_key: str = Field(..., env="API_SECRET_KEY")

    # Database
    database_url: str = Field("sqlite+aiosqlite:///./alpaca_trading.db", env="DATABASE_URL")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_to_file: bool = Field(True, env="LOG_TO_FILE")

    class Config:
        import os
        # Get the directory where this config file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        env_file = os.path.join(config_dir, ".env")
        case_sensitive = False


# Global settings instance
settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance"""
    global settings
    if settings is None:
        settings = Settings()
    return settings
