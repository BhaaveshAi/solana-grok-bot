import time
import threading
import random
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# --- PLATFORM STATE ($100 START) ---
platform_state = {
    "equity": 100.00,
    "starting_equity": 100.00,
    "live_mode": False,
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
    "order_book": {
        "bids": [[194.15, 12.4], [194.10, 45.2], [194.00, 110.5]],
        "asks": [[194.25, 8.1], [194.30, 33.4], [194.40, 95.0]]
    },
    "trading_news": [
        {"time": "Just now", "headline": "Solana DEX volume surges past $2.5B amid high perpetual demand.", "sentiment": "BULLISH"},
        {"time": "8m ago", "headline": "Macro liquidity inflows trigger aggressive short-covering across majors.", "sentiment": "BULLISH"}
    ],
    "agent_telemetry": [
        "[Scout Agent]: Scanning 50+ perpetual order books...",
        "[Risk Agent]: Volatility check passed. Margin allocated.",
        "[Execution Agent]: Momentum breakout confirmed on SOL/USDT."
    ],
    "big_closes": [
        {"symbol": "XLM", "side": "SHORT", "lev": "10x", "profit": 30},
        {"symbol": "ETH", "side": "LONG", "lev": "16x", "profit": 63},
        {"symbol": "BCH", "side": "LONG", "lev": "16x", "profit": 153},
        {"symbol": "AVAX", "side": "LONG", "lev": "11x", "profit": 312},
        {"symbol": "BNB", "side": "SHORT", "lev": "23x", "profit": 500}
    ]
}

def background_simulation_loop():
    symbols = [
        ("SOL/USDT", "LONG", 12, 180, 195, 45),
        ("XLM/USDT", "SHORT", 10, 0.39, 0.18, 25),
        ("ETH/USDT", "LONG", 16, 2400, 2480, 60),
        ("AVAX/USDT", "LONG", 11, 9.04, 9.74, 120)
    ]
    idx = 0
    while True:
        try:
            time.sleep(4)
            sym, side, lev, entry, target, base_profit = symbols[idx % len(symbols)]
            idx += 1

            pnl_pct = random.randint(10, 50)
            unrealized = round((platform_state["equity"] * 0.25) * (pnl_pct / 100) * (lev / 10), 2)

            platform_state["active_position"] = {
                "symbol": sym.split('/')[0],
                "type": side,
                "leverage": lev,
                "entry": entry,
                "current": target if pnl_pct > 35 else entry * 1.04,
                "tp_price": target,
                "tp_hit": pnl_pct > 35,
                "unrealized_pnl": unrealized,
                "pnl_pct": pnl_pct,
                "margin": round(platform_state["equity"] * 0.25, 2),
                "sparkline": [entry, entry * 1.01, entry * 1.03, target]
            }

            if pnl_pct > 35:
                realized = base_profit // 2
                platform_state["equity"] = round(platform_state["equity"] + realized, 2)
                platform_state["big_closes"].insert(0, {
                    "symbol": sym.split('/')[0],
                    "side": side,
                    "lev": f"{lev}x",
                    "profit": int(realized)
                })
                if len(platform_state["big_closes"]) > 5:
                    platform_state["big_closes"].pop()
                platform_state["agent_telemetry"].insert(0, f"[Automated Bot]: TP executed on {sym} (+${realized})")

        except Exception as e:
            print(f"Loop error: {e}")

threading.Thread(target=background_simulation_loop, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def get_state():
    return jsonify(platform_state)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)