"""
REST API for External Control and Monitoring
"""
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import os

from config import get_settings
from bot import TradingBot
from core.risk_manager import RiskManager
from loguru import logger

# Initialize FastAPI
app = FastAPI(
    title="ASTER Trading Bot API",
    description="API for controlling and monitoring the ASTER trading bot",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for serving images and other static assets
# This allows serving files like aster-logo.png from the root directory
static_dir = os.path.dirname(os.path.dirname(__file__))
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Security
settings = get_settings()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Global bot instance
bot_instance: Optional[TradingBot] = None


# Models
class BotConfig(BaseModel):
    symbols: List[str]
    enabled_strategies: Optional[List[str]] = None
    interval_seconds: int = 60


class PositionResponse(BaseModel):
    symbol: str
    side: str
    entry_price: float
    quantity: float
    leverage: int
    stop_loss: Optional[float]
    take_profit: Optional[float]
    unrealized_pnl: float
    liquidation_price: Optional[float]


class StatisticsResponse(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    current_capital: float
    roi: float
    open_positions: int
    daily_pnl: float
    max_drawdown: float


class TradeResponse(BaseModel):
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    leverage: int
    pnl: float
    pnl_percentage: float
    entry_time: datetime
    exit_time: datetime
    strategy: str


# Security dependency
async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.api_secret_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# Endpoints
@app.get("/")
async def root():
    """Redirect to dashboard"""
    dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dashboard.html')
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {
        "name": "ASTER Trading Bot API",
        "version": "1.0.0",
        "status": "running" if bot_instance and bot_instance.is_running else "stopped"
    }

@app.get("/admin-dashboard")
async def admin_dashboard():
    """Serve admin dashboard with absolute values"""
    admin_dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin-dashboard.html')
    if os.path.exists(admin_dashboard_path):
        return FileResponse(admin_dashboard_path)
    return {
        "error": "Admin dashboard not found"
    }

@app.get("/api")
async def api_info():
    """API info endpoint"""
    return {
        "name": "ASTER Trading Bot API",
        "version": "1.0.0",
        "status": "running" if bot_instance and bot_instance.is_running else "stopped"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_running": bot_instance.is_running if bot_instance else False
    }


@app.post("/bot/start", dependencies=[Depends(verify_api_key)])
async def start_bot(config: BotConfig):
    """Start the trading bot"""
    global bot_instance

    if bot_instance and bot_instance.is_running:
        raise HTTPException(status_code=400, detail="Bot is already running")

    try:
        # Initialize bot
        bot_instance = TradingBot(
            symbols=config.symbols,
            enabled_strategies=config.enabled_strategies
        )

        # Start bot in background
        asyncio.create_task(run_bot_async(config.interval_seconds))

        return {
            "status": "success",
            "message": "Bot started successfully",
            "symbols": config.symbols,
            "strategies": [s.name for s in bot_instance.strategies]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")


async def run_bot_async(interval_seconds: int):
    """Run bot in async context"""
    if bot_instance:
        bot_instance.start(interval_seconds)


@app.post("/bot/stop", dependencies=[Depends(verify_api_key)])
async def stop_bot():
    """Stop the trading bot"""
    global bot_instance

    if not bot_instance or not bot_instance.is_running:
        raise HTTPException(status_code=400, detail="Bot is not running")

    try:
        bot_instance.stop()

        return {
            "status": "success",
            "message": "Bot stopped successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop bot: {str(e)}")


@app.get("/bot/status", dependencies=[Depends(verify_api_key)])
async def get_bot_status():
    """Get bot status"""
    if not bot_instance:
        return {
            "running": False,
            "message": "Bot not initialized"
        }

    stats = bot_instance.risk_manager.get_statistics()

    # Get regime info if dynamic selector enabled
    regime_info = None
    if bot_instance.use_dynamic_selector and bot_instance.strategy_selector:
        regime_stats = bot_instance.strategy_selector.get_stats()
        regime_info = {
            "current_regime": regime_stats['regime'].get('current_regime', 'unknown'),
            "confidence": regime_stats['regime'].get('confidence', 0),
            "selected_strategy": bot_instance.selected_strategy_name,
            "strategy_performance": regime_stats['strategies']
        }

    return {
        "running": bot_instance.is_running,
        "symbols": bot_instance.symbols,
        "strategies": [s.name for s in bot_instance.strategies],
        "statistics": stats,
        "dynamic_selector_enabled": bot_instance.use_dynamic_selector,
        "regime_info": regime_info
    }


@app.get("/positions", response_model=List[PositionResponse], dependencies=[Depends(verify_api_key)])
async def get_positions():
    """Get all open positions"""
    if not bot_instance:
        raise HTTPException(status_code=400, detail="Bot not initialized")

    positions = []

    for symbol, position in bot_instance.risk_manager.positions.items():
        positions.append(PositionResponse(
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            quantity=position.quantity,
            leverage=position.leverage,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            unrealized_pnl=position.unrealized_pnl,
            liquidation_price=position.liquidation_price
        ))

    return positions


@app.get("/positions/{symbol}", response_model=PositionResponse, dependencies=[Depends(verify_api_key)])
async def get_position(symbol: str):
    """Get specific position"""
    if not bot_instance:
        raise HTTPException(status_code=400, detail="Bot not initialized")

    if symbol not in bot_instance.risk_manager.positions:
        raise HTTPException(status_code=404, detail=f"No position found for {symbol}")

    position = bot_instance.risk_manager.positions[symbol]

    return PositionResponse(
        symbol=position.symbol,
        side=position.side,
        entry_price=position.entry_price,
        quantity=position.quantity,
        leverage=position.leverage,
        stop_loss=position.stop_loss,
        take_profit=position.take_profit,
        unrealized_pnl=position.unrealized_pnl,
        liquidation_price=position.liquidation_price
    )


@app.delete("/positions/{symbol}", dependencies=[Depends(verify_api_key)])
async def close_position(symbol: str):
    """Manually close a position"""
    if not bot_instance:
        raise HTTPException(status_code=400, detail="Bot not initialized")

    if symbol not in bot_instance.risk_manager.positions:
        raise HTTPException(status_code=404, detail=f"No position found for {symbol}")

    try:
        # Get current price
        ticker = bot_instance.client.get_ticker_price(symbol)
        current_price = float(ticker['price'])

        # Close position
        position = bot_instance.risk_manager.positions[symbol]
        side = "SELL" if position.side == "LONG" else "BUY"

        # Place market order to close
        order = bot_instance.client.create_order(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=position.quantity,
            reduce_only=True
        )

        # Close in risk manager
        trade = bot_instance.risk_manager.close_position(symbol, current_price, "manual_close")

        return {
            "status": "success",
            "message": f"Position closed for {symbol}",
            "pnl": trade.pnl if trade else 0.0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close position: {str(e)}")


@app.get("/statistics", response_model=StatisticsResponse, dependencies=[Depends(verify_api_key)])
async def get_statistics():
    """Get trading statistics"""
    if not bot_instance:
        raise HTTPException(status_code=400, detail="Bot not initialized")

    stats = bot_instance.risk_manager.get_statistics()

    return StatisticsResponse(**stats)


@app.get("/trades", response_model=List[TradeResponse], dependencies=[Depends(verify_api_key)])
async def get_trades(limit: int = 50):
    """Get trade history"""
    if not bot_instance:
        raise HTTPException(status_code=400, detail="Bot not initialized")

    trades = bot_instance.risk_manager.trades[-limit:]

    return [
        TradeResponse(
            symbol=trade.symbol,
            side=trade.side,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price,
            quantity=trade.quantity,
            leverage=trade.leverage,
            pnl=trade.pnl,
            pnl_percentage=trade.pnl_percentage,
            entry_time=trade.entry_time,
            exit_time=trade.exit_time,
            strategy=trade.strategy
        )
        for trade in trades
    ]


@app.get("/market/{symbol}", dependencies=[Depends(verify_api_key)])
async def get_market_data(symbol: str, interval: str = "5m", limit: int = 100):
    """Get market data for a symbol"""
    if not bot_instance:
        raise HTTPException(status_code=400, detail="Bot not initialized")

    try:
        df = bot_instance.get_market_data(symbol, interval, limit)

        return {
            "symbol": symbol,
            "interval": interval,
            "data": df.to_dict(orient='records')
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")


@app.post("/manual-trade", dependencies=[Depends(verify_api_key)])
async def manual_trade(
    symbol: str,
    side: str,
    quantity: float,
    leverage: int,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None
):
    """Execute a manual trade"""
    if not bot_instance:
        raise HTTPException(status_code=400, detail="Bot not initialized")

    try:
        # Validate inputs
        if side not in ["LONG", "SHORT"]:
            raise HTTPException(status_code=400, detail="Side must be LONG or SHORT")

        # Get current price
        ticker = bot_instance.client.get_ticker_price(symbol)
        current_price = float(ticker['price'])

        # Create signal
        signal = {
            'action': side,
            'entry_price': current_price,
            'stop_loss': stop_loss or (current_price * 0.98 if side == "LONG" else current_price * 1.02),
            'take_profit': take_profit,
            'leverage': leverage,
            'confidence': 1.0,
            'reason': 'Manual trade'
        }

        # Execute
        success = bot_instance.execute_signal(symbol, signal, "manual")

        if success:
            return {
                "status": "success",
                "message": f"Trade executed: {side} {quantity} {symbol}",
                "entry_price": current_price
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to execute trade")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute manual trade: {str(e)}")


@app.get("/dashboard/summary")
async def get_dashboard_summary():
    """Get complete dashboard summary (no auth required for easy phone access)"""
    if not bot_instance:
        return {
            "running": False,
            "message": "Bot not initialized"
        }

    # Get internal stats (we'll override some values with real data from Aster)
    stats = bot_instance.risk_manager.get_statistics()

    # FETCH REAL BALANCE AND METRICS FROM ASTER API
    try:
        # Use account endpoint to get complete account info
        account_data = bot_instance.client.get_account_info()
        account_equity = float(account_data.get('totalWalletBalance', 0))
        maintenance_margin = float(account_data.get('totalMaintMargin', 0))
        unrealized_pnl = float(account_data.get('totalUnrealizedProfit', 0))

        # Calculate PnL and trade stats from CLOSED POSITIONS (trades with realized PnL from Aster)
        aster_all_trades = bot_instance.client.get_account_trades(limit=100)

        # Filter trades with realized PnL (position closures)
        closed_trades = [t for t in aster_all_trades if abs(float(t.get('realizedPnl', 0))) > 0.01]

        total_realized_pnl = sum(float(trade.get('realizedPnl', 0)) for trade in closed_trades)

        # Calculate win rate from closed trades
        winning_trades = sum(1 for trade in closed_trades if float(trade.get('realizedPnl', 0)) > 0)
        total_trades_count = len(closed_trades)
        win_rate = (winning_trades / total_trades_count * 100) if total_trades_count > 0 else 0.0

        # Get FIXED INITIAL BALANCE from DB (set ONCE, never changes)
        initial_balance = bot_instance.state_manager.get_initial_balance()

        if initial_balance is None:
            # First time - calculate TRUE initial capital and save to DB PERMANENTLY
            # Formula: Current Equity - Total Realized PnL = Original Starting Capital
            calculated_initial = account_equity - total_realized_pnl
            bot_instance.state_manager.set_initial_balance(calculated_initial)
            initial_balance = calculated_initial
            logger.info(f"✅ Initial balance set in DB (FIXED): ${initial_balance:.2f}")

        # ROI based on FIXED initial balance (only changes when trades close, NOT when prices move)
        real_roi = (total_realized_pnl / initial_balance) * 100 if initial_balance > 0 else 0.0

        # Optional: ROI including unrealized (for total performance tracking)
        total_pnl_with_unrealized = total_realized_pnl + unrealized_pnl
        roi_total = (total_pnl_with_unrealized / initial_balance) * 100 if initial_balance > 0 else 0.0

        # Calculate daily PnL (trades from last 24 hours)
        now = datetime.now()
        cutoff_time_ms = int((now.timestamp() - 86400) * 1000)  # 24 hours ago
        daily_pnl = sum(float(trade.get('realizedPnl', 0)) for trade in closed_trades
                       if int(trade.get('time', 0)) > cutoff_time_ms)

        logger.info(f"📊 Account Equity: ${account_equity:.2f} | Initial (FIXED): ${initial_balance:.2f} | Realized PnL: ${total_realized_pnl:.2f} | Unrealized: ${unrealized_pnl:.2f} | Trades: {total_trades_count} | Win Rate: {win_rate:.2f}% | ROI: {real_roi:.2f}% | ROI Total: {roi_total:.2f}%")

        # Update last known balance in DB
        bot_instance.state_manager.update_last_balance(account_equity)

        # OVERRIDE stats with REAL values from Aster
        stats['current_capital'] = round(account_equity, 2)
        stats['initial_capital'] = round(initial_balance, 2)  # FIXED, never changes
        stats['maintenance_margin'] = round(maintenance_margin, 2)
        stats['total_pnl'] = round(total_realized_pnl, 2)
        stats['unrealized_pnl'] = round(unrealized_pnl, 2)
        stats['daily_pnl'] = round(daily_pnl, 2)
        stats['roi'] = round(real_roi, 2)  # Stable ROI (only realized)
        stats['total_trades'] = total_trades_count
        stats['winning_trades'] = winning_trades
        stats['losing_trades'] = total_trades_count - winning_trades
        stats['win_rate'] = round(win_rate, 2)

    except Exception as e:
        logger.error(f"Error fetching account data from Aster: {e}")
        # Fallback to internal calculated values if API call fails
        stats['maintenance_margin'] = 0.0
        stats['unrealized_pnl'] = 0.0

    # Get regime info directly from regime detector
    regime_info = None
    if bot_instance.use_dynamic_selector and bot_instance.strategy_selector:
        regime_detector = bot_instance.strategy_selector.regime_detector

        # Get current regime and confidence
        current_regime = regime_detector.current_regime.value if regime_detector.current_regime else 'unknown'
        confidence = regime_detector.regime_confidence

        # Get regime stats
        regime_stats = bot_instance.strategy_selector.get_stats()

        regime_info = {
            "current_regime": current_regime,
            "confidence": confidence,
            "selected_strategy": bot_instance.selected_strategy_name,
            "regime_distribution": regime_stats['regime'].get('regime_distribution', {}),
            "strategy_performance": regime_stats['strategies']
        }

    # Get open positions with real-time data from Aster
    positions = []
    try:
        # Fetch all positions directly from Aster API
        aster_positions = bot_instance.client.get_position_info()

        # Create a map of Aster positions by symbol
        aster_positions_map = {}
        for aster_pos in aster_positions:
            symbol = aster_pos['symbol']
            position_amt = float(aster_pos.get('positionAmt', 0))
            if position_amt != 0:  # Only active positions
                aster_positions_map[symbol] = {
                    'current_price': float(aster_pos.get('markPrice', 0)),
                    'unrealized_pnl': float(aster_pos.get('unRealizedProfit', 0)),
                    'liquidation_price': float(aster_pos.get('liquidationPrice', 0))
                }

        # Match with bot's tracked positions
        for symbol, position in bot_instance.risk_manager.positions.items():
            if symbol in aster_positions_map:
                # Use real-time data from Aster
                aster_data = aster_positions_map[symbol]
                # Calculate hold time
                hold_time = (datetime.now() - position.entry_time).total_seconds() / 3600  # hours
                positions.append({
                    "symbol": symbol,
                    "side": position.side,
                    "entry_price": position.entry_price,
                    "current_price": aster_data['current_price'],
                    "quantity": position.quantity,
                    "leverage": position.leverage,
                    "unrealized_pnl": round(aster_data['unrealized_pnl'], 2),
                    "stop_loss": position.stop_loss,
                    "take_profit": position.take_profit,
                    "liquidation_price": aster_data['liquidation_price'],
                    "strategy": position.strategy,
                    "hold_time_hours": round(hold_time, 2)
                })
            else:
                # Fallback if position not found on Aster (shouldn't happen)
                hold_time = (datetime.now() - position.entry_time).total_seconds() / 3600
                positions.append({
                    "symbol": symbol,
                    "side": position.side,
                    "entry_price": position.entry_price,
                    "current_price": position.entry_price,
                    "quantity": position.quantity,
                    "leverage": position.leverage,
                    "unrealized_pnl": position.unrealized_pnl,
                    "stop_loss": position.stop_loss,
                    "take_profit": position.take_profit,
                    "liquidation_price": position.liquidation_price,
                    "strategy": position.strategy,
                    "hold_time_hours": round(hold_time, 2)
                })
    except Exception as e:
        logger.error(f"Error fetching positions from Aster: {e}")
        # Fallback to stored positions if API call fails
        for symbol, position in bot_instance.risk_manager.positions.items():
            hold_time = (datetime.now() - position.entry_time).total_seconds() / 3600
            positions.append({
                "symbol": symbol,
                "side": position.side,
                "entry_price": position.entry_price,
                "current_price": position.entry_price,
                "quantity": position.quantity,
                "leverage": position.leverage,
                "unrealized_pnl": position.unrealized_pnl,
                "stop_loss": position.stop_loss,
                "take_profit": position.take_profit,
                "liquidation_price": position.liquidation_price,
                "strategy": position.strategy,
                "hold_time_hours": round(hold_time, 2)
            })

    # Get ALL trades from DATABASE (persistent across restarts!)
    # Import is now handled at startup in start_bot_auto.py, NOT here
    all_internal_trades = []
    recent_trades = []
    try:
        # Simply load trades from database - import already happened at startup
        db_trades = bot_instance.state_manager.get_all_trades()

        # Convert database trades to API format
        for db_trade in db_trades:
            trade_data = {
                "symbol": db_trade['symbol'],
                "side": db_trade['side'],
                "entry_price": db_trade['entry_price'],
                "exit_price": db_trade['exit_price'],
                "pnl": round(db_trade['pnl'], 2),
                "pnl_percentage": round(db_trade['pnl_percentage'], 2),
                "strategy": db_trade['strategy'],
                "entry_time": db_trade['entry_time'],
                "exit_time": db_trade['exit_time']
            }
            all_internal_trades.append(trade_data)

        # Recent trades = last 10 for display
        recent_trades = all_internal_trades[:10] if len(all_internal_trades) > 10 else all_internal_trades

        logger.info(f"✅ Loaded {len(all_internal_trades)} trades from database")

    except Exception as e:
        logger.error(f"Error fetching trades from database: {e}")
        all_internal_trades = []
        recent_trades = []

    # Calculate strategy performance aggregates FROM DATABASE TRADES
    # Use database trades (they have strategy names assigned!)
    # Initialize with ALL strategies (even if no trades yet)
    strategy_stats = {}

    # Pre-populate with all available strategies
    for strategy in bot_instance.strategies:
        strategy_stats[strategy.name] = {
            "total_trades": 0,
            "winning_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_hold_time_hours": 0.0,
            "total_hold_time": 0.0
        }

    try:
        # Use database trades (they have correct strategy names!)
        for trade in all_internal_trades:
            strategy = trade['strategy']

            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "total_pnl": 0.0,
                    "win_rate": 0.0,
                    "avg_hold_time_hours": 0.0,
                    "total_hold_time": 0.0
                }

            strategy_stats[strategy]["total_trades"] += 1
            strategy_stats[strategy]["total_pnl"] += trade['pnl']
            if trade['pnl'] > 0:
                strategy_stats[strategy]["winning_trades"] += 1

            # Calculate hold time from timestamps
            try:
                if isinstance(trade['entry_time'], str):
                    entry_dt = datetime.fromisoformat(trade['entry_time'].replace('Z', '+00:00'))
                else:
                    entry_dt = trade['entry_time']

                if isinstance(trade['exit_time'], str):
                    exit_dt = datetime.fromisoformat(trade['exit_time'].replace('Z', '+00:00'))
                else:
                    exit_dt = trade['exit_time']

                hold_time = (exit_dt - entry_dt).total_seconds() / 3600
                strategy_stats[strategy]["total_hold_time"] += hold_time
            except:
                pass  # Skip if timestamp parsing fails

    except Exception as e:
        logger.error(f"Error calculating strategy stats from database trades: {e}")
        # Keep the pre-populated strategy stats even on error

    # Calculate averages and percentages
    for strategy in strategy_stats:
        total = strategy_stats[strategy]["total_trades"]
        if total > 0:
            strategy_stats[strategy]["win_rate"] = (strategy_stats[strategy]["winning_trades"] / total) * 100
            # Only recalculate avg_hold_time if we have actual hold time data (from fallback path)
            if strategy_stats[strategy]["total_hold_time"] > 0:
                strategy_stats[strategy]["avg_hold_time_hours"] = round(strategy_stats[strategy]["total_hold_time"] / total, 2)

        # Clean up temporary field
        if "total_hold_time" in strategy_stats[strategy]:
            del strategy_stats[strategy]["total_hold_time"]

        # Round values
        strategy_stats[strategy]["total_pnl"] = round(strategy_stats[strategy]["total_pnl"], 2)
        strategy_stats[strategy]["win_rate"] = round(strategy_stats[strategy]["win_rate"], 2)

    # Calculate additional metrics WITH REAL-TIME DATA
    # Build capital curve from initial balance + realized PnL from Aster trades
    try:
        initial_bal = bot_instance.state_manager.get_initial_balance() or bot_instance.risk_manager.initial_capital
        aster_trades_for_curve = bot_instance.client.get_account_trades(limit=200)

        # Build capital curve from realized trades
        capital_curve = [initial_bal]
        for trade in reversed(aster_trades_for_curve):
            realized_pnl = float(trade.get('realizedPnl', 0))
            if abs(realized_pnl) > 0.01:
                capital_curve.append(capital_curve[-1] + realized_pnl)

        # Add current unrealized PnL to get REAL-TIME equity
        current_equity_with_unrealized = capital_curve[-1] + stats.get('unrealized_pnl', 0)

        # Calculate drawdown including unrealized PnL
        peak = max(capital_curve + [current_equity_with_unrealized])
        current_drawdown = ((peak - current_equity_with_unrealized) / peak) * 100 if peak > 0 else 0.0

        # Max drawdown from historical capital curve
        max_dd = 0.0
        for i in range(len(capital_curve)):
            local_peak = max(capital_curve[:i+1])
            dd = ((local_peak - capital_curve[i]) / local_peak) * 100 if local_peak > 0 else 0.0
            max_dd = max(max_dd, dd)

        # Override max_drawdown with calculated value
        stats['max_drawdown'] = round(max_dd, 2)

        # Average hold time calculation
        all_trades = bot_instance.risk_manager.trades
        if all_trades:
            total_hold_time = sum((t.exit_time - t.entry_time).total_seconds() / 3600 for t in all_trades)
            avg_hold_time = total_hold_time / len(all_trades)
        else:
            avg_hold_time = 0.0

    except Exception as e:
        logger.error(f"Error calculating drawdown metrics: {e}")
        current_drawdown = 0.0
        avg_hold_time = 0.0

    return {
        "timestamp": datetime.now().isoformat(),
        "bot_status": {
            "running": bot_instance.is_running,
            "symbols": bot_instance.symbols,
            "dynamic_selector": bot_instance.use_dynamic_selector,
            "agent_address": settings.aster_signer_address,
            "blockchain": "ethereum"
        },
        "statistics": {
            "current_capital": stats['current_capital'],
            "initial_capital": stats.get('initial_capital', 0.0),
            "maintenance_margin": stats.get('maintenance_margin', 0.0),
            "unrealized_pnl": stats.get('unrealized_pnl', 0.0),
            "total_pnl": stats['total_pnl'],
            "roi": stats['roi'],
            "win_rate": stats['win_rate'],
            "total_trades": stats['total_trades'],
            "winning_trades": stats['winning_trades'],
            "losing_trades": stats['losing_trades'],
            "open_positions": stats['open_positions'],
            "daily_pnl": stats['daily_pnl'],
            "max_drawdown": stats['max_drawdown'],
            "current_drawdown": round(current_drawdown, 2),
            "avg_hold_time_hours": round(avg_hold_time, 2)
        },
        "regime_info": regime_info,
        "strategy_performance": strategy_stats,
        "open_positions": positions,
        "recent_trades": recent_trades,
        "all_internal_trades": all_internal_trades  # For chart temporal data
    }


@app.get("/dashboard/closed-positions")
async def get_closed_positions(limit: int = 50):
    """
    Get closed positions from Aster exchange trade history (no auth for easy access)
    This fetches actual trade data directly from Aster API
    """
    if not bot_instance:
        return {
            "error": "Bot not initialized",
            "closed_positions": []
        }

    try:
        # Fetch account trades from Aster
        account_trades = bot_instance.client.get_account_trades(limit=limit * 2)  # Get more since we need to pair entry/exit

        # Group trades by symbol and organize into closed positions
        # Each closed position should have an entry and an exit trade
        closed_positions = []

        # Process trades - we need to identify position openings and closings
        # Trades are returned with most recent first, so reverse to process chronologically
        trades_by_symbol = {}
        for trade in reversed(account_trades):
            symbol = trade.get('symbol')
            if symbol not in trades_by_symbol:
                trades_by_symbol[symbol] = []
            trades_by_symbol[symbol].append(trade)

        # For each symbol, match buy/sell pairs to identify closed positions
        for symbol, trades in trades_by_symbol.items():
            # Simple approach: just show all trades as they are
            # The API returns trades with side (BUY/SELL), price, qty, time, etc.
            for trade in trades[-limit:]:  # Limit per symbol
                side = trade.get('side', 'UNKNOWN')
                price = float(trade.get('price', 0))
                qty = float(trade.get('qty', 0))
                realized_pnl = float(trade.get('realizedPnl', 0))
                commission = float(trade.get('commission', 0))
                time_ms = int(trade.get('time', 0))
                trade_time = datetime.fromtimestamp(time_ms / 1000) if time_ms else datetime.now()

                closed_positions.append({
                    "symbol": symbol,
                    "side": side,
                    "price": price,
                    "quantity": qty,
                    "realized_pnl": round(realized_pnl, 2),
                    "commission": round(commission, 4),
                    "time": trade_time.isoformat(),
                    "trade_id": trade.get('id', '')
                })

        # Sort by time descending (most recent first)
        closed_positions.sort(key=lambda x: x['time'], reverse=True)

        return {
            "closed_positions": closed_positions[:limit],
            "count": len(closed_positions[:limit])
        }

    except Exception as e:
        logger.error(f"Error fetching closed positions from Aster: {e}")
        return {
            "error": str(e),
            "closed_positions": []
        }


# =============================================================================
# NEW API ENDPOINTS FOR FRONTEND TEAM
# These endpoints provide data in the format requested by the frontend team
# They use existing data from /dashboard/summary without any structural changes
# =============================================================================

@app.get("/api/bot/metrics")
async def get_bot_metrics():
    """
    Get bot metrics and trading models performance
    Format compatible with frontend team requirements
    No authentication required for easy access
    """
    if not bot_instance:
        return {
            "error": "Bot not initialized",
            "timestamp": datetime.now().isoformat()
        }

    try:
        # Get data from existing dashboard summary endpoint
        summary_data = await get_dashboard_summary()

        stats = summary_data.get("statistics", {})
        strategy_performance = summary_data.get("strategy_performance", {})
        bot_status = summary_data.get("bot_status", {})

        # Determine bot status
        bot_running = bot_status.get("running", False)
        status = "LIVE" if bot_running else "PAUSED"

        # Build global metrics
        global_metrics = {
            "totalVolume": round(stats.get("current_capital", 0), 2),
            "uptime": 94.23,  # Static for now, could be calculated from bot start time
            "roi": round(stats.get("roi", 0), 2),
            "activeModels": len([s for s in strategy_performance.values() if s.get("total_trades", 0) > 0]),
            "winRate": round(stats.get("win_rate", 0), 2),
            "totalTrades": stats.get("total_trades", 0),
            "dailyPnL": round(stats.get("daily_pnl", 0), 2),
            "status": status
        }

        # Build trading models from strategy performance
        trading_models = []

        for strategy_name, perf in strategy_performance.items():
            total_pnl = perf.get("total_pnl", 0)
            total_trades = perf.get("total_trades", 0)
            win_rate = perf.get("win_rate", 0)

            # Calculate PnL percentage based on initial capital
            initial_capital = stats.get("initial_capital", 1)
            pnl_percent = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

            # Determine status (active if has trades)
            model_status = "ACTIVE" if total_trades > 0 else "PAUSED"

            # Generate performance sparkline data (50 points) from REAL trade history
            performance_data = []

            # Get all trades for this strategy from internal trades
            strategy_trades = [t for t in summary_data.get("all_internal_trades", []) if t.get("strategy") == strategy_name]

            if len(strategy_trades) >= 10:
                # Use real trade data - calculate cumulative win rate over time
                # Take every Nth trade to get 50 points, or pad/interpolate
                step = max(1, len(strategy_trades) // 50)
                wins = 0
                total_checked = 0

                for i in range(0, len(strategy_trades), step):
                    if len(performance_data) >= 50:
                        break

                    trade = strategy_trades[i]
                    total_checked += 1
                    if trade.get("pnl", 0) > 0:
                        wins += 1

                    current_wr = (wins / total_checked * 100) if total_checked > 0 else 0
                    performance_data.append(round(current_wr, 1))

                # Pad to 50 points if needed
                while len(performance_data) < 50:
                    performance_data.append(performance_data[-1] if performance_data else 0)

            elif total_trades > 0:
                # Few trades - use simple interpolation from 0 to current win rate
                for i in range(50):
                    progress = i / 49  # 0 to 1
                    interpolated_wr = win_rate * progress
                    performance_data.append(round(interpolated_wr, 1))
            else:
                # No trades - return flat zeros
                performance_data = [0] * 50

            trading_models.append({
                "name": strategy_name,
                "pnl": round(total_pnl, 2),
                "isPositive": total_pnl >= 0,
                "trades": total_trades,
                "winRate": round(win_rate, 2),
                "status": model_status,
                "confidence": round(win_rate, 1) if win_rate > 0 else 50.0,
                "strategies": [strategy_name],  # Single strategy per model
                "description": f"Trading strategy using {strategy_name} approach",
                "performanceData": performance_data
            })

        return {
            "timestamp": datetime.now().isoformat(),
            "globalMetrics": global_metrics,
            "tradingModels": trading_models
        }

    except Exception as e:
        logger.error(f"Error in /api/bot/metrics: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/chart/performance")
async def get_chart_performance(timeframe: str = "1m", points: int = 150):
    """
    Get chart performance data for graphing
    Format compatible with frontend team requirements
    No authentication required for easy access

    Args:
        timeframe: Time interval (1m, 5m, 15m, 1h, 4h, 1d)
        points: Number of data points to return (default 150)
    """
    if not bot_instance:
        return {
            "error": "Bot not initialized",
            "timestamp": datetime.now().isoformat()
        }

    try:
        # Get data from existing dashboard summary
        summary_data = await get_dashboard_summary()

        stats = summary_data.get("statistics", {})
        all_trades = summary_data.get("all_internal_trades", [])
        strategy_performance = summary_data.get("strategy_performance", {})

        # Build data points from trade history with interpolation
        data_points = []

        if all_trades and len(all_trades) > 0:
            # Sort trades by exit time
            sorted_trades = sorted(all_trades, key=lambda x: x.get("exit_time", ""))

            # Build base data points from actual trades
            base_points = []
            cumulative_pnl = 0

            for trade in sorted_trades:
                exit_time = trade.get("exit_time", "")
                pnl_percent = trade.get("pnl_percentage", 0)
                cumulative_pnl += pnl_percent

                if exit_time:
                    try:
                        dt = datetime.fromisoformat(exit_time)
                        base_points.append({
                            "time": dt.strftime("%H:%M"),
                            "value": round(cumulative_pnl, 2),
                            "timestamp": int(dt.timestamp() * 1000)
                        })
                    except:
                        pass

            # If we have fewer points than requested, interpolate
            if len(base_points) >= points:
                # Take evenly spaced points
                step = len(base_points) / points
                for i in range(points):
                    idx = int(i * step)
                    if idx < len(base_points):
                        data_points.append(base_points[idx])
            elif len(base_points) > 0:
                # Interpolate between existing points to reach requested count
                if len(base_points) == 1:
                    # Only one trade - create linear growth from 0 to current PnL
                    start_time = base_points[0]["timestamp"] - (3600000 * 24)  # 24 hours before
                    end_time = base_points[0]["timestamp"]
                    final_value = base_points[0]["value"]

                    for i in range(points):
                        progress = i / (points - 1)
                        interpolated_time = int(start_time + (end_time - start_time) * progress)
                        interpolated_value = final_value * progress

                        dt = datetime.fromtimestamp(interpolated_time / 1000)
                        data_points.append({
                            "time": dt.strftime("%H:%M"),
                            "value": round(interpolated_value, 2),
                            "timestamp": interpolated_time
                        })
                else:
                    # Multiple trades - create smooth interpolation
                    points_per_segment = max(1, points // len(base_points))

                    for i in range(len(base_points) - 1):
                        current = base_points[i]
                        next_point = base_points[i + 1]

                        # Add current point
                        data_points.append(current)

                        # Interpolate between current and next
                        for j in range(1, points_per_segment):
                            progress = j / points_per_segment
                            interpolated_time = int(current["timestamp"] + (next_point["timestamp"] - current["timestamp"]) * progress)
                            interpolated_value = current["value"] + (next_point["value"] - current["value"]) * progress

                            dt = datetime.fromtimestamp(interpolated_time / 1000)
                            data_points.append({
                                "time": dt.strftime("%H:%M"),
                                "value": round(interpolated_value, 2),
                                "timestamp": interpolated_time
                            })

                    # Add final point
                    data_points.append(base_points[-1])

                    # Trim to requested count
                    if len(data_points) > points:
                        step = len(data_points) / points
                        data_points = [data_points[int(i * step)] for i in range(points)]
        else:
            # No trades - create flat line at zero
            now = datetime.now()
            start_time = now.timestamp() - (3600 * 24)  # 24 hours ago

            for i in range(points):
                timestamp = int((start_time + (now.timestamp() - start_time) * (i / (points - 1))) * 1000)
                dt = datetime.fromtimestamp(timestamp / 1000)
                data_points.append({
                    "time": dt.strftime("%H:%M"),
                    "value": 0,
                    "timestamp": timestamp
                })

        # Ensure we have at least one point
        if not data_points:
            now = datetime.now()
            data_points.append({
                "time": now.strftime("%H:%M"),
                "value": 0,
                "timestamp": int(now.timestamp() * 1000)
            })

        # Build AI models performance (top 3 strategies by PnL)
        ai_models = []

        # Sort strategies by total PnL
        sorted_strategies = sorted(
            strategy_performance.items(),
            key=lambda x: x[1].get("total_pnl", 0),
            reverse=True
        )[:3]  # Top 3

        model_icons = ["🤖", "🧠", "💎"]
        model_colors = [
            "rgb(240, 185, 11)",
            "rgb(218, 165, 32)",
            "rgb(255, 215, 0)"
        ]

        for idx, (strategy_name, perf) in enumerate(sorted_strategies):
            total_pnl = perf.get("total_pnl", 0)

            ai_models.append({
                "name": strategy_name,
                "icon": model_icons[idx] if idx < len(model_icons) else "🔮",
                "value": round(total_pnl, 2),
                "subValue": round(total_pnl * 0.9, 2),  # Previous value (simplified)
                "color": model_colors[idx] if idx < len(model_colors) else "rgb(200, 200, 200)"
            })

        # Calculate statistics from data points
        if data_points:
            values = [dp["value"] for dp in data_points]
            min_val = min(values)
            max_val = max(values)
            avg_val = sum(values) / len(values)

            # Calculate volatility (standard deviation)
            variance = sum((v - avg_val) ** 2 for v in values) / len(values)
            std_dev = variance ** 0.5
            volatility = (std_dev / avg_val * 100) if avg_val != 0 else 0
        else:
            min_val = max_val = avg_val = volatility = 0

        return {
            "timestamp": datetime.now().isoformat(),
            "timeframe": timeframe,
            "dataPoints": data_points,
            "aiModels": ai_models,
            "statistics": {
                "min": round(min_val, 2),
                "max": round(max_val, 2),
                "average": round(avg_val, 2),
                "volatility": round(abs(volatility), 2)
            }
        }

    except Exception as e:
        logger.error(f"Error in /api/chart/performance: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/bot/positions")
async def get_open_positions():
    """
    Get all currently open positions with real-time data

    Returns:
        {
            "timestamp": "2025-10-23T16:50:00",
            "totalPositions": 2,
            "totalUnrealizedPnL": -1.36,
            "totalExposure": 2345.67,
            "positions": [
                {
                    "symbol": "BTCUSDT",
                    "side": "LONG",
                    "entryPrice": 109372.5,
                    "currentPrice": 109897.79,
                    "quantity": 0.011,
                    "leverage": 20,
                    "unrealizedPnL": -5.78,
                    "unrealizedPnLPercentage": -0.48,
                    "stopLoss": 111013.09,
                    "takeProfit": 107731.91,
                    "liquidationPrice": 173214.57,
                    "strategy": "Breakout Scalping",
                    "entryTime": "2025-10-23T15:30:00",
                    "holdTimeHours": 1.33,
                    "exposure": 1202.97,
                    "margin": 60.15
                }
            ]
        }
    """
    try:
        if not bot_instance:
            raise HTTPException(status_code=503, detail="Bot not initialized")

        positions_data = []
        total_unrealized_pnl = 0.0
        total_exposure = 0.0

        # Get all open positions
        for symbol, position in bot_instance.risk_manager.positions.items():
            try:
                # Get current price from exchange
                current_price = bot_instance.client.get_current_price(symbol)

                # Calculate unrealized PnL
                if position.side == "LONG":
                    pnl_per_unit = current_price - position.entry_price
                else:  # SHORT
                    pnl_per_unit = position.entry_price - current_price

                unrealized_pnl = pnl_per_unit * position.quantity
                unrealized_pnl_percentage = (pnl_per_unit / position.entry_price) * 100

                # Calculate exposure and margin
                exposure = current_price * position.quantity
                margin = exposure / position.leverage

                # Calculate hold time
                hold_time_hours = (datetime.now() - position.entry_time).total_seconds() / 3600

                total_unrealized_pnl += unrealized_pnl
                total_exposure += exposure

                position_data = {
                    "symbol": symbol,
                    "side": position.side,
                    "entryPrice": round(position.entry_price, 2),
                    "currentPrice": round(current_price, 2),
                    "quantity": position.quantity,
                    "leverage": position.leverage,
                    "unrealizedPnL": round(unrealized_pnl, 2),
                    "unrealizedPnLPercentage": round(unrealized_pnl_percentage, 2),
                    "stopLoss": round(position.stop_loss, 2) if position.stop_loss else None,
                    "takeProfit": round(position.take_profit, 2) if position.take_profit else None,
                    "liquidationPrice": round(position.liquidation_price, 2) if position.liquidation_price else None,
                    "strategy": position.strategy,
                    "entryTime": position.entry_time.isoformat(),
                    "holdTimeHours": round(hold_time_hours, 2),
                    "exposure": round(exposure, 2),
                    "margin": round(margin, 2)
                }

                positions_data.append(position_data)

            except Exception as e:
                logger.error(f"Error processing position {symbol}: {e}")
                continue

        return {
            "timestamp": datetime.now().isoformat(),
            "totalPositions": len(positions_data),
            "totalUnrealizedPnL": round(total_unrealized_pnl, 2),
            "totalExposure": round(total_exposure, 2),
            "positions": positions_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/bot/positions: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
