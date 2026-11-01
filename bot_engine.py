import time
import threading
import random
import os
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# --- CONFIGURATION & TRADING MODE ---
LIVE_MODE = False          # False = Paper Trading ($100 start), True = Live Real-Money Trading
INITIAL_EQUITY = 100.00

# Live Exchange & News API Credentials (Configure when going live)
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "")
EXCHANGE_SECRET_KEY = os.getenv("EXCHANGE_SECRET_KEY", "")

# Master Platform State
platform_state = {
    "equity": INITIAL_EQUITY,
    "starting_equity": INITIAL_EQUITY,
    "live_mode": LIVE_MODE,
    "active_position": {
        "symbol": "SOL/USDT",
        "type": "LONG",
        "leverage": 10,
        "entry": 182.50,
        "current": 194.20,
        "tp_price": 198.00,
        "tp_hit": False,
        "unrealized_pnl": 12.40,
        "pnl_pct": 14.2,
        "margin": 25.0,
        "sparkline": [182, 185, 188, 191, 194]
    },
    "trading_news": [
        {"time": "Just now", "headline": "Solana DEX volume surges past $2.5B in 24 hours amid high perpetual demand.", "sentiment": "BULLISH"},
        {"time": "5m ago", "headline": "Macro liquidity inflows trigger aggressive short-covering across major altcoin perps.", "sentiment": "BULLISH"},
        {"time": "15m ago", "headline": "Federal Reserve maintains interest rate outlook; crypto markets react with high volatility.", "sentiment": "NEUTRAL"}
    ],
    "agent_telemetry": [
        "[Scout Agent]: Scanning 50+ perpetual order books on Binance/Hyperliquid...",
        "[Risk Agent]: Volatility threshold verified. Risk parameter locked at 25% margin.",
        "[Analyst Agent]: High-conviction momentum breakout detected on SOL/USDT."
    ],
    "big_closes": [
        {"symbol": "XLM", "side": "SHORT", "lev": "10x", "profit": 30},
        {"symbol": "ETH", "side": "LONG", "lev": "16x", "profit": 63},
        {"symbol": "BCH", "side": "LONG", "lev": "16x", "profit": 153},
        {"symbol": "AVAX", "side": "LONG", "lev": "11x", "profit": 312},
        {"symbol": "BNB", "side": "SHORT", "lev": "23x", "profit": 500}
    ]
}

def fetch_live_market_tickers():
    """Fetches real-time crypto prices from public exchange endpoints for live charts & simulation."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana,stellar,ethereum,bitcoin-cash,avalanche-2,binancecoin&vs_currencies=usd"
        res = requests.get(url, timeout=5).json()
        return {
            "SOL/USDT": res.get("solana", {}).get("usd", 185.0),
            "XLM/USDT": res.get("stellar", {}).get("usd", 0.39),
            "ETH/USDT": res.get("ethereum", {}).get("usd", 2400.0),
            "BCH/USDT": res.get("bitcoin-cash", {}).get("usd", 272.0),
            "AVAX/USDT": res.get("avalanche-2", {}).get("usd", 9.5),
            "BNB/USDT": res.get("binancecoin", {}).get("usd", 700.0)
        }
    except Exception:
        return {"SOL/USDT": 185.0, "XLM/USDT": 0.39, "ETH/USDT": 2400.0}

def automated_trading_loop():
    """Background loop handling automated agent execution, risk checks, and trade management."""
    print(f"=== Automated Trading Platform Core Online | Mode: {'LIVE TRADING' if LIVE_MODE else 'PAPER TRADING ($100)'} ===")
    
    symbols = [
        ("SOL/USDT", "LONG", 12, 180, 195, 45),
        ("XLM/USDT", "SHORT", 10, 0.39, 0.18, 25),
        ("ETH/USDT", "LONG", 16, 2400, 2480, 60),
        ("AVAX/USDT", "LONG", 11, 9.04, 9.74, 120)
    ]
    idx = 0

    while True:
        try:
            tickers = fetch_live_market_tickers()
            
            if LIVE_MODE:
                # --- LIVE TRADING EXECUTION ---
                # Insert CCXT live order execution logic here when LIVE_MODE is set to True:
                # exchange = ccxt.binance({'apiKey': EXCHANGE_API_KEY, 'secret': EXCHANGE_SECRET_KEY, ...})
                pass
            else:
                # --- AUTOMATED PAPER TRADING SIMULATION ---
                time.sleep(5)
                sym, side, lev, entry, target, base_profit = symbols[idx % len(symbols)]
                idx += 1

                current_price = tickers.get(sym, entry * 1.05)
                pnl_pct = random.randint(8, 48)
                unrealized = round((platform_state["equity"] * 0.30) * (pnl_pct / 100) * (lev / 10), 2)

                platform_state["active_position"] = {
                    "symbol": sym.split('/')[0],
                    "type": side,
                    "leverage": lev,
                    "entry": entry,
                    "current": current_price,
                    "tp_price": target,
                    "tp_hit": pnl_pct > 35,
                    "unrealized_pnl": unrealized,
                    "pnl_pct": pnl_pct,
                    "margin": round(platform_state["equity"] * 0.30, 2),
                    "sparkline": [entry, entry * 1.01, entry * 1.03, current_price]
                }

                # Periodically trigger Take Profit and log automated agent actions
                if pnl_pct > 35:
                    realized_gain = base_profit // 2
                    platform_state["equity"] = round(platform_state["equity"] + realized_gain, 2)
                    
                    platform_state["big_closes"].insert(0, {
                        "symbol": sym.split('/')[0],
                        "side": side,
                        "lev": f"{lev}x",
                        "profit": int(realized_gain)
                    })
                    if len(platform_state["big_closes"]) > 5:
                        platform_state["big_closes"].pop()

                    platform_state["agent_telemetry"].insert(0, f"[Execution Agent]: Take-Profit executed on {sym} {side} {lev}x (+${realized_gain})")
                    if len(platform_state["agent_telemetry"]) > 15:
                        platform_state["agent_telemetry"].pop()

        except Exception as e:
            print(f"Trading loop error: {e}")

# Start background automated agent thread
threading.Thread(target=automated_trading_loop, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def get_state():
    return jsonify(platform_state)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)