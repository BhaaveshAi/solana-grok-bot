import time
import threading
import random
import requests
from flask import Flask, jsonify, render_template

# --- CONFIGURATION & STATE ---
app = Flask(__name__)

portfolio = {
    "equity": 100.00,
    "starting_equity": 100.00,
    "multiplier": 1.0,
    "runtime_str": "00:01 / 24H",
    "active_position": {
        "symbol": "XLM",
        "type": "SHORT",
        "leverage": 10,
        "entry": 0.39466,
        "current": 0.1899,
        "tp_price": 0.17830,
        "tp_hit": True,
        "unrealized_pnl": 4.50,
        "pnl_pct": 7.0,
        "margin": 25.0,
        "sparkline": [0.39, 0.35, 0.32, 0.28, 0.24, 0.19]
    },
    "trade_tape_stats": {"v": 3, "l": 6, "score": 85},
    "trade_tape_logs": [
        "SHORT XLM opened at $0.39466",
        "Price movement tracked: -12.4%",
        "Take Profit target locked at $0.17830"
    ],
    "big_closes": [
        {"symbol": "XLM", "side": "SHORT", "lev": "10x", "profit": 30},
        {"symbol": "ETH", "side": "LONG", "lev": "16x", "profit": 63},
        {"symbol": "BCH", "side": "LONG", "lev": "16x", "profit": 153},
        {"symbol": "AVAX", "side": "LONG", "lev": "11x", "profit": 312},
        {"symbol": "BNB", "side": "SHORT", "lev": "23x", "profit": 500}
    ]
}

def simulation_worker():
    symbols = [
        ("XLM", "SHORT", 10, 0.39, 0.18, 25),
        ("ETH", "LONG", 16, 2400, 2460, 45),
        ("BCH", "LONG", 16, 237, 272, 85),
        ("AVAX", "LONG", 11, 9.04, 9.74, 120),
        ("BNB", "SHORT", 23, 700, 722, 210)
    ]
    idx = 0
    while True:
        try:
            time.sleep(6)
            sym, side, lev, entry, target, profit = symbols[idx % len(symbols)]
            idx += 1
            
            portfolio["active_position"] = {
                "symbol": sym,
                "type": side,
                "leverage": lev,
                "entry": entry,
                "current": target,
                "tp_price": target,
                "tp_hit": True,
                "unrealized_pnl": float(profit) / 3,
                "pnl_pct": random.randint(15, 85),
                "margin": 20,
                "sparkline": [entry, entry*0.95, entry*0.90, target]
            }
            portfolio["equity"] += 15.0
            portfolio["trade_tape_logs"].insert(0, f"TP HIT: {sym} {side} {lev}x (+${profit})")
        except Exception as e:
            print(f"[SIMULATION ERROR] {e}")

# Start background simulation thread safely
threading.Thread(target=simulation_worker, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def get_state():
    return jsonify(portfolio)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)