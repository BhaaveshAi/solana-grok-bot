import time
import threading
import random
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# --- PAPER TRADING DESK STATE ($100.00 START) ---
portfolio = {
    "equity": 100.00,
    "starting_equity": 100.00,
    "multiplier": 10.0,
    "runtime_hours": 0.2,
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

def local_simulation_worker():
    print("=== Grok Bot Local Simulation Loop Active ($100 Capital) ===")
    mock_market = [
        ("XLM", "SHORT", 10, 0.39, 0.18, 25),
        ("ETH", "LONG", 16, 2400, 2460, 45),
        ("BCH", "LONG", 16, 237, 272, 85),
        ("AVAX", "LONG", 11, 9.04, 9.74, 120),
        ("SOL", "LONG", 20, 180, 195, 150),
        ("BNB", "SHORT", 23, 700, 722, 210)
    ]
    idx = 0
    
    while True:
        try:
            time.sleep(5)
            sym, side, lev, entry, target, profit_val = mock_market[idx % len(mock_market)]
            idx += 1
            
            # Simulate dynamic price ticks and PnL scaling
            pnl_pct = random.randint(12, 92)
            unrealized = round(profit_val * (pnl_pct / 100), 2)
            
            portfolio["active_position"] = {
                "symbol": sym,
                "type": side,
                "leverage": lev,
                "entry": entry,
                "current": target,
                "tp_price": target,
                "tp_hit": True,
                "unrealized_pnl": unrealized,
                "pnl_pct": pnl_pct,
                "margin": 20,
                "sparkline": [entry, entry * 0.96, entry * 0.92, target]
            }
            
            # Every few cycles, close the trade into equity & big closes
            if idx % 2 == 0:
                portfolio["equity"] = round(portfolio["equity"] + unrealized, 2)
                portfolio["big_closes"].insert(0, {
                    "symbol": sym,
                    "side": side,
                    "lev": f"{lev}x",
                    "profit": int(unrealized + 10)
                })
                if len(portfolio["big_closes"]) > 5:
                    portfolio["big_closes"].pop()
                portfolio["trade_tape_logs"].insert(0, f"TP HIT: {sym} {side} {lev}x (+${unrealized})")

            portfolio["runtime_hours"] = round(portfolio["runtime_hours"] + 0.01, 2)
        except Exception as e:
            print(f"Loop error: {e}")

# Run simulation loop in background thread
threading.Thread(target=local_simulation_worker, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def get_state():
    return jsonify(portfolio)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)