"""
Demo Dashboard - Runs without real Aster credentials

Shows dashboard with simulated data so you can see how it looks
"""
import sys
import threading
import time
from datetime import datetime
from typing import Dict, List
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger
import random
import os

# Initialize FastAPI
app = FastAPI(title="ASTER Trading Bot Demo")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simulated bot state
demo_state = {
    "running": True,
    "current_capital": 10000,
    "initial_capital": 10000,
    "total_pnl": 0,
    "daily_pnl": 0,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "open_positions": [],
    "recent_trades": [],
    "current_regime": "high_vol_trending",
    "regime_confidence": 0.85,
    "selected_strategy": "Breakout Scalping",
    "strategy_stats": {
        "Breakout Scalping": {
            "total_trades": 45,
            "win_rate": 0.64,
            "total_pnl": 2340,
            "avg_pnl": 52,
            "enabled": True
        },
        "Momentum Reversal": {
            "total_trades": 28,
            "win_rate": 0.57,
            "total_pnl": 1120,
            "avg_pnl": 40,
            "enabled": True
        },
        "Funding Arbitrage": {
            "total_trades": 12,
            "win_rate": 0.75,
            "total_pnl": 890,
            "avg_pnl": 74,
            "enabled": True
        },
        "Liquidation Cascade": {
            "total_trades": 8,
            "win_rate": 0.50,
            "total_pnl": -120,
            "avg_pnl": -15,
            "enabled": False
        },
        "Market Making": {
            "total_trades": 67,
            "win_rate": 0.78,
            "total_pnl": 1870,
            "avg_pnl": 28,
            "enabled": True
        }
    }
}


def simulate_market_updates():
    """Simulate market activity"""
    regimes = ["high_vol_trending", "low_vol_ranging", "momentum_exhaustion", "mixed"]
    strategies = ["Breakout Scalping", "Momentum Reversal", "Market Making", "Funding Arbitrage"]

    while True:
        time.sleep(15)  # Update every 15 seconds

        # Randomly change regime sometimes
        if random.random() < 0.1:  # 10% chance
            demo_state["current_regime"] = random.choice(regimes)
            demo_state["selected_strategy"] = random.choice(strategies)
            demo_state["regime_confidence"] = random.uniform(0.6, 0.95)
            logger.info(f"Regime changed to: {demo_state['current_regime']}")

        # Simulate new trade sometimes
        if random.random() < 0.15:  # 15% chance
            is_win = random.random() < 0.62  # 62% win rate
            pnl = random.uniform(30, 120) if is_win else random.uniform(-80, -20)

            demo_state["total_trades"] += 1
            if is_win:
                demo_state["winning_trades"] += 1
            else:
                demo_state["losing_trades"] += 1

            demo_state["total_pnl"] += pnl
            demo_state["daily_pnl"] += pnl
            demo_state["current_capital"] = demo_state["initial_capital"] + demo_state["total_pnl"]

            trade = {
                "symbol": "BTCUSDT",
                "side": random.choice(["LONG", "SHORT"]),
                "entry_price": random.uniform(48000, 52000),
                "exit_price": 0,
                "pnl": pnl,
                "pnl_percentage": (pnl / demo_state["current_capital"]) * 100,
                "strategy": demo_state["selected_strategy"],
                "entry_time": datetime.now().isoformat(),
                "exit_time": datetime.now().isoformat()
            }
            trade["exit_price"] = trade["entry_price"] * (1 + trade["pnl_percentage"]/100)

            demo_state["recent_trades"].append(trade)
            if len(demo_state["recent_trades"]) > 10:
                demo_state["recent_trades"] = demo_state["recent_trades"][-10:]

            logger.info(f"Simulated trade: {trade['side']} ${pnl:.2f}")

        # Simulate position changes
        if random.random() < 0.2 and len(demo_state["open_positions"]) < 2:
            # Open position
            pos = {
                "symbol": "BTCUSDT",
                "side": random.choice(["LONG", "SHORT"]),
                "entry_price": random.uniform(48000, 52000),
                "current_price": 0,
                "quantity": random.uniform(0.05, 0.2),
                "leverage": random.choice([20, 30, 35, 45]),
                "unrealized_pnl": 0,
                "stop_loss": 0,
                "take_profit": 0
            }
            pos["current_price"] = pos["entry_price"] * random.uniform(0.98, 1.02)
            pos["unrealized_pnl"] = (pos["current_price"] - pos["entry_price"]) * pos["quantity"] * pos["leverage"]
            if pos["side"] == "SHORT":
                pos["unrealized_pnl"] *= -1
            pos["stop_loss"] = pos["entry_price"] * 0.98 if pos["side"] == "LONG" else pos["entry_price"] * 1.02
            pos["take_profit"] = pos["entry_price"] * 1.03 if pos["side"] == "LONG" else pos["entry_price"] * 0.97

            demo_state["open_positions"].append(pos)
            logger.info(f"Opened position: {pos['side']} {pos['symbol']}")

        elif demo_state["open_positions"] and random.random() < 0.3:
            # Close position
            demo_state["open_positions"].pop(0)
            logger.info("Closed position")

        # Update existing positions
        for pos in demo_state["open_positions"]:
            pos["current_price"] *= random.uniform(0.998, 1.002)
            pos["unrealized_pnl"] = (pos["current_price"] - pos["entry_price"]) * pos["quantity"] * pos["leverage"]
            if pos["side"] == "SHORT":
                pos["unrealized_pnl"] *= -1


@app.get("/")
async def root():
    """Serve dashboard"""
    dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard.html')
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"message": "Dashboard not found"}


@app.get("/dashboard/summary")
async def get_dashboard_summary():
    """Get dashboard data"""

    win_rate = (demo_state["winning_trades"] / demo_state["total_trades"] * 100) if demo_state["total_trades"] > 0 else 0
    roi = (demo_state["total_pnl"] / demo_state["initial_capital"] * 100) if demo_state["initial_capital"] > 0 else 0

    return {
        "timestamp": datetime.now().isoformat(),
        "bot_status": {
            "running": demo_state["running"],
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "dynamic_selector": True
        },
        "statistics": {
            "current_capital": demo_state["current_capital"],
            "total_pnl": demo_state["total_pnl"],
            "roi": roi,
            "win_rate": win_rate,
            "total_trades": demo_state["total_trades"],
            "winning_trades": demo_state["winning_trades"],
            "losing_trades": demo_state["losing_trades"],
            "open_positions": len(demo_state["open_positions"]),
            "daily_pnl": demo_state["daily_pnl"],
            "max_drawdown": -5.2
        },
        "regime_info": {
            "current_regime": demo_state["current_regime"],
            "confidence": demo_state["regime_confidence"],
            "selected_strategy": demo_state["selected_strategy"],
            "regime_distribution": {
                "high_vol_trending": 45,
                "low_vol_ranging": 30,
                "momentum_exhaustion": 15,
                "mixed": 10
            },
            "strategy_performance": demo_state["strategy_stats"]
        },
        "open_positions": demo_state["open_positions"],
        "recent_trades": demo_state["recent_trades"]
    }


def main():
    """Main entry point"""
    print("="*70)
    print("ASTER Trading Bot - DEMO MODE")
    print("="*70)
    print("\nDashboard starting...")
    print("\nThis is a DEMO with simulated data")
    print("   No real trading or exchange connection")
    print("   Just to show you how the dashboard looks!\n")

    # Start market simulator in background
    simulator_thread = threading.Thread(target=simulate_market_updates, daemon=True)
    simulator_thread.start()

    # Add some initial trades
    for i in range(5):
        is_win = random.random() < 0.6
        pnl = random.uniform(30, 120) if is_win else random.uniform(-80, -20)

        demo_state["total_trades"] += 1
        if is_win:
            demo_state["winning_trades"] += 1
        else:
            demo_state["losing_trades"] += 1

        demo_state["total_pnl"] += pnl
        demo_state["daily_pnl"] += pnl

        trade = {
            "symbol": "BTCUSDT",
            "side": random.choice(["LONG", "SHORT"]),
            "entry_price": random.uniform(48000, 52000),
            "exit_price": 0,
            "pnl": pnl,
            "pnl_percentage": (pnl / 10000) * 100,
            "strategy": random.choice(["Breakout Scalping", "Momentum Reversal", "Market Making"]),
            "entry_time": datetime.now().isoformat(),
            "exit_time": datetime.now().isoformat()
        }
        trade["exit_price"] = trade["entry_price"] * (1 + trade["pnl_percentage"]/100)
        demo_state["recent_trades"].append(trade)

    demo_state["current_capital"] = demo_state["initial_capital"] + demo_state["total_pnl"]

    print("="*70)
    print("DASHBOARD READY!")
    print("="*70)
    print("\nOpen in browser:")
    print(f"   http://localhost:8000/")
    print("\nFrom phone (same WiFi):")
    print(f"   http://<YOUR_LOCAL_IP>:8000/")
    print("\nTo find your local IP:")
    print("   Run: ipconfig (look for IPv4 Address)")
    print("\nThe dashboard will auto-refresh every 10 seconds")
    print("   You'll see simulated trades appearing!\n")
    print("="*70)
    print("\nPress Ctrl+C to stop\n")

    # Start API server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
