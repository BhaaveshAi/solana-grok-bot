import time
import threading
import requests
from flask import Flask, jsonify, render_template

# --- CONFIGURATION & TRADING SETTINGS ---
PAPER_MODE = True  # Set to False later when going live with real API keys
INITIAL_EQUITY = 59.89
LEVERAGE = 10

# In-Memory Trading Portfolio State
portfolio = {
    "equity": INITIAL_EQUITY,
    "starting_equity": INITIAL_EQUITY,
    "active_position": None,
    "trade_tape": [],
    "big_closes": [],
    "runtime_hours": 0.1
}

# --- MARKET DATA & STRATEGY AGENT ---
def fetch_crypto_prices():
    """Fetches live prices for top crypto perps."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=stellar,ethereum,bitcoin,avalanche-2,binancecoin&vs_currencies=usd"
    try:
        res = requests.get(url, timeout=10).json()
        return {
            "XLM": res.get("stellar", {}).get("usd", 0.12),
            "ETH": res.get("ethereum", {}).get("usd", 2400.0),
            "BCH": res.get("bitcoin-cash", {}).get("usd", 270.0) or 272.0,
            "AVAX": res.get("avalanche-2", {}).get("usd", 9.5),
            "BNB": res.get("binancecoin", {}).get("usd", 700.0)
        }
    except Exception:
        return {"XLM": 0.12, "ETH": 2400.0, "BCH": 272.0, "AVAX": 9.5, "BNB": 700.0}

def trading_desk_loop():
    print("=== Grok Bot Perpetual Futures Desk Active (Paper Mode) ===")
    symbols = ["XLM", "ETH", "BCH", "AVAX", "BNB"]
    
    while True:
        prices = fetch_crypto_prices()
        
        # If no active position, open one
        if not portfolio["active_position"]:
            import random
            sym = random.choice(symbols)
            entry_p = prices.get(sym, 100.0)
            side = random.choice(["LONG", "SHORT"])
            margin = portfolio["equity"] * 0.5  # Use 50% equity per trade
            
            portfolio["active_position"] = {
                "symbol": sym,
                "side": side,
                "leverage": LEVERAGE,
                "entry_price": entry_p,
                "current_price": entry_p,
                "margin": margin,
                "unrealized_pnl": 0.0,
                "pnl_pct": 0.0,
                "tp_price": entry_p * 1.05 if side == "LONG" else entry_p * 0.95
            }
            portfolio["trade_tape"].append(f"Opened {side} {sym} @ ${entry_p}")
        else:
            # Update position price & calculate PnL
            pos = portfolio["active_position"]
            sym = pos["symbol"]
            curr_p = prices.get(sym, pos["entry_price"])
            pos["current_price"] = curr_p
            
            price_diff_pct = (curr_p - pos["entry_price"]) / pos["entry_price"]
            if pos["side"] == "SHORT":
                price_diff_pct = -price_diff_pct
                
            pos["pnl_pct"] = price_diff_pct * pos["leverage"]
            pos["unrealized_pnl"] = pos["margin"] * pos["pnl_pct"]
            
            # Close trade if take profit or stop loss hit (+15% or -10%)
            if pos["pnl_pct"] >= 0.15 or pos["pnl_pct"] <= -0.10:
                realized = pos["margin"] + pos["unrealized_pnl"]
                portfolio["equity"] += pos["unrealized_pnl"]
                
                portfolio["big_closes"].insert(0, {
                    "symbol": sym,
                    "side": pos["side"],
                    "leverage": pos["leverage"],
                    "profit": pos["unrealized_pnl"]
                })
                
                portfolio["trade_tape"].append(f"Closed {pos['side']} {sym} | PnL: ${pos['unrealized_pnl']:.2f}")
                portfolio["active_position"] = None
                
        portfolio["runtime_hours"] += 0.05
        time.sleep(10)

# --- FLASK REST API & WEB DASHBOARD ---
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state', methods=['GET'])
def get_state():
    return jsonify(portfolio)

if __name__ == "__main__":
    t = threading.Thread(target=trading_desk_loop, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000)