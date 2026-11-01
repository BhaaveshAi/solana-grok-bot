import time
import threading
import random
import requests
from flask import Flask, jsonify, render_template

# --- CONFIGURATION & SETTINGS ---
INITIAL_EQUITY = 59.89
LEVERAGE = 10

# Portfolio State
portfolio = {
    "equity": INITIAL_EQUITY,
    "starting_equity": INITIAL_EQUITY,
    "active_position": None,
    "trade_tape": [],
    "big_closes": [],
    "runtime_hours": 1.2
}

# --- SIMULATED PERPETUAL TRADING ENGINE ---
def fetch_crypto_prices():
    """Fetches live market prices for perps."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=stellar,ethereum,bitcoin-cash,avalanche-2,binancecoin&vs_currencies=usd"
        res = requests.get(url, timeout=5).json()
        return {
            "XLM": res.get("stellar", {}).get("usd", 0.12),
            "ETH": res.get("ethereum", {}).get("usd", 2400.0),
            "BCH": res.get("bitcoin-cash", {}).get("usd", 272.0),
            "AVAX": res.get("avalanche-2", {}).get("usd", 9.5),
            "BNB": res.get("binancecoin", {}).get("usd", 700.0)
        }
    except Exception:
        return {"XLM": 0.12, "ETH": 2400.0, "BCH": 272.0, "AVAX": 9.5, "BNB": 700.0}

def trading_simulation_loop():
    print("=== Grok Bot Perpetual Futures Desk Active (Paper Run) ===")
    symbols = ["XLM", "ETH", "BCH", "AVAX", "BNB"]
    
    while True:
        prices = fetch_crypto_prices()
        
        # If no active position, open a new one
        if not portfolio["active_position"]:
            sym = random.choice(symbols)
            entry_p = prices.get(sym, 100.0)
            side = random.choice(["LONG", "SHORT"])
            margin = portfolio["equity"] * 0.45
            
            portfolio["active_position"] = {
                "symbol": sym,
                "side": side,
                "leverage": random.choice([10, 16, 23]),
                "entry_price": entry_p,
                "current_price": entry_p,
                "margin": margin,
                "unrealized_pnl": 0.0,
                "pnl_pct": 0.0,
                "tp_price": entry_p * 1.08 if side == "LONG" else entry_p * 0.92
            }
            portfolio["trade_tape"].insert(0, f"[OPEN] {side} {sym} @ ${entry_p}")
        else:
            pos = portfolio["active_position"]
            sym = pos["symbol"]
            curr_p = prices.get(sym, pos["entry_price"])
            
            # Simulate slight price fluctuation towards profit
            fluctuation = random.uniform(-0.005, 0.012)
            curr_p = curr_p * (1 + fluctuation)
            pos["current_price"] = curr_p
            
            diff_pct = (curr_p - pos["entry_price"]) / pos["entry_price"]
            if pos["side"] == "SHORT":
                diff_pct = -diff_pct
                
            pos["pnl_pct"] = diff_pct * pos["leverage"]
            pos["unrealized_pnl"] = pos["margin"] * pos["pnl_pct"]
            
            # Take profit trigger (+18%) or stop loss (-10%)
            if pos["pnl_pct"] >= 0.18 or pos["pnl_pct"] <= -0.10:
                profit = pos["unrealized_pnl"]
                portfolio["equity"] += profit
                
                portfolio["big_closes"].insert(0, {
                    "symbol": sym,
                    "side": pos["side"],
                    "profit": profit
                })
                
                portfolio["trade_tape"].insert(0, f"[TP HIT] {sym} +${profit:.2f}")
                portfolio["active_position"] = None

        portfolio["runtime_hours"] += 0.03
        time.sleep(5)

# --- FLASK WEB SERVER ---
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state', methods=['GET'])
def get_state():
    return jsonify(portfolio)

if __name__ == "__main__":
    threading.Thread(target=trading_simulation_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)