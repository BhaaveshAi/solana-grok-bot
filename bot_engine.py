import time
import threading
import random
import os
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# --- CONFIGURATION & SWITCH ---
LIVE_MODE = False  # Keep False for Paper Trading ($100 start). Set to True when going live.
INITIAL_EQUITY = 100.00

# Live Exchange API Keys (Configure these when switching LIVE_MODE = True)
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "")
EXCHANGE_SECRET_KEY = os.getenv("EXCHANGE_SECRET_KEY", "")

# Master Portfolio State
portfolio = {
    "equity": INITIAL_EQUITY,
    "starting_equity": INITIAL_EQUITY,
    "multiplier": 10.0,
    "runtime_str": "00:01 / 24H",
    "active_position": {
        "symbol": "SOL",
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
    "trade_tape_logs": [
        "Connected to Perpetual Execution Core",
        "Scouting high-conviction order books...",
        "LONG SOL 10x position initialized."
    ],
    "big_closes": [
        {"symbol": "XLM", "side": "SHORT", "lev": "10x", "profit": 30},
        {"symbol": "ETH", "side": "LONG", "lev": "16x", "profit": 63},
        {"symbol": "BCH", "side": "LONG", "lev": "16x", "profit": 153},
        {"symbol": "AVAX", "side": "LONG", "lev": "11x", "profit": 312},
        {"symbol": "BNB", "side": "SHORT", "lev": "23x", "profit": 500}
    ]
}

def trading_engine_worker():
    """Handles either Paper Trading simulation or Live Exchange execution loop."""
    print(f"=== Grok Bot Core Started | Mode: {'LIVE TRADING' if LIVE_MODE else 'PAPER TRADING ($100)'} ===")
    
    symbols = [
        ("SOL", "LONG", 12, 180, 195, 45),
        ("XLM", "SHORT", 10, 0.39, 0.18, 25),
        ("ETH", "LONG", 16, 2400, 2480, 60),
        ("BCH", "LONG", 16, 237, 272, 85),
        ("AVAX", "LONG", 11, 9.04, 9.74, 120),
        ("BNB", "SHORT", 23, 700, 722, 150)
    ]
    idx = 0

    while True:
        try:
            if LIVE_MODE:
                # --- LIVE EXECUTION HOOK ---
                # When you go live, replace this block with CCXT / Exchange API calls:
                # e.g., exchange.create_market_order(...) and fetch live account balance.
                pass
            else:
                # --- PAPER TRADING SIMULATION LOOP ---
                time.sleep(4)
                sym, side, lev, entry, target, base_profit = symbols[idx % len(symbols)]
                idx += 1

                # Simulate active market fluctuations
                pnl_pct = random.randint(5, 45)
                unrealized = round((portfolio["equity"] * 0.25) * (pnl_pct / 100) * (lev / 10), 2)

                portfolio["active_position"] = {
                    "symbol": sym,
                    "type": side,
                    "leverage": lev,
                    "entry": entry,
                    "current": target if pnl_pct > 30 else entry * 1.05,
                    "tp_price": target,
                    "tp_hit": pnl_pct > 35,
                    "unrealized_pnl": unrealized,
                    "pnl_pct": pnl_pct,
                    "margin": round(portfolio["equity"] * 0.25, 2),
                    "sparkline": [entry, entry * 1.02, entry * 1.04, target]
                }

                # Periodically take profit and close trade into equity
                if pnl_pct > 35:
                    profit_realized = base_profit // 3
                    portfolio["equity"] = round(portfolio["equity"] + profit_realized, 2)
                    
                    portfolio["big_closes"].insert(0, {
                        "symbol": sym,
                        "side": side,
                        "lev": f"{lev}x",
                        "profit": int(profit_realized)
                    })
                    if len(portfolio["big_closes"]) > 5:
                        portfolio["big_closes"].pop()

                    portfolio["trade_tape_logs"].insert(0, f"TP HIT: {sym} {side} {lev}x (+${profit_realized})")
                    if len(portfolio["trade_tape_logs"]) > 20:
                        portfolio["trade_tape_logs"].pop()

        except Exception as e:
            print(f"Engine Error: {e}")

# Start background trading loop thread
threading.Thread(target=trading_engine_worker, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def get_state():
    return jsonify({
        **portfolio,
        "live_mode": LIVE_MODE
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)