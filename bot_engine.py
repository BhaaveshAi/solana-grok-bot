import os
import json
import time
import random
import threading
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Configuration & State File
LIVE_MODE = False  # Set to True when API keys are configured in Render
INITIAL_EQUITY = 20.0  # Configurable starting capital (e.g., $20 test deposit)
STATE_FILE = "platform_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state file: {e}")
    
    # Default initial state if file doesn't exist
    return {
        "balance": INITIAL_EQUITY,
        "equity": INITIAL_EQUITY,
        "realized_pnl": 0.0,
        "active_position": None,
        "trades_history": [],
        "telemetry": [],
        "market_prices": {
            "SOLUSDT": 161.13,
            "BTCUSDT": 62917.54,
            "ETHUSDT": 3514.70,
            "AVAXUSDT": 24.48,
            "BNBUSDT": 652.65
        }
    }

def save_state():
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(platform_state, f, indent=4)
    except Exception as e:
        print(f"Error saving state file: {e}")

platform_state = load_state()

agents_registry = [
    {"name": "SOL Volatility Scout", "pair": "SOLUSDT", "bias": "LONG"},
    {"name": "BTC Macro Quant Agent", "pair": "BTCUSDT", "bias": "LONG"},
    {"name": "ETH Derivatives Bot", "pair": "ETHUSDT", "bias": "SHORT"},
    {"name": "AVAX Breakout Specialist", "pair": "AVAXUSDT", "bias": "LONG"},
    {"name": "BNB Liquidity Agent", "pair": "BNBUSDT", "bias": "SHORT"}
]

def background_trading_engine():
    while True:
        try:
            time.sleep(3.0)
            
            # Simulate natural price fluctuations
            for pair in platform_state["market_prices"]:
                fluctuation = random.uniform(-0.003, 0.003)
                platform_state["market_prices"][pair] = round(platform_state["market_prices"][pair] * (1 + fluctuation), 2)

            pos = platform_state["active_position"]
            
            if pos:
                # Update active position PnL based on current price
                current_price = platform_state["market_prices"][pos["pair"]]
                entry = pos["entry"]
                leverage = pos["leverage"]
                margin = pos["margin"]
                
                if pos["side"] == "LONG":
                    pnl_pct = (current_price - entry) / entry
                else:
                    pnl_pct = (entry - current_price) / entry
                    
                unrealized = margin * leverage * pnl_pct
                pos["current_price"] = current_price
                pos["unrealized_pnl"] = round(unrealized, 2)
                pos["pnl_percentage"] = round(pnl_pct * 100 * leverage, 2)
                
                # Check take profit (+15%) or stop loss (-10%)
                if pnl_pct * leverage >= 0.15 or pnl_pct * leverage <= -0.10:
                    trigger_type = "AUTO_TAKE_PROFIT" if pnl_pct >= 0 else "AUTO_STOP_LOSS"
                    close_trade(trigger_type)
            else:
                agent = random.choice(agents_registry)
                pair = agent["pair"]
                price = platform_state["market_prices"][pair]
                side = agent["bias"]
                leverage = random.choice([5, 10, 16, 20])
                
                available_balance = platform_state["equity"]
                if available_balance < 3.0:
                    platform_state["balance"] = INITIAL_EQUITY
                    platform_state["equity"] = INITIAL_EQUITY
                    available_balance = INITIAL_EQUITY

                margin = round(available_balance * 0.25, 2)
                if margin < 1.0: margin = 1.0

                platform_state["active_position"] = {
                    "agent": agent["name"],
                    "pair": pair,
                    "side": side,
                    "leverage": leverage,
                    "entry": price,
                    "current_price": price,
                    "margin": margin,
                    "unrealized_pnl": 0.0,
                    "pnl_percentage": 0.0,
                    "time": time.strftime("%I:%M:%S %p")
                }
                
                log_msg = f"[{agent['name']}]: EXECUTED {side} ON {pair} {leverage}x @ ${price}"
                platform_state["telemetry"].insert(0, log_msg)
                if len(platform_state["telemetry"]) > 30:
                    platform_state["telemetry"].pop()

            save_state()

        except Exception as e:
            print(f"Engine Error: {e}")

def close_trade(trigger_method):
    pos = platform_state["active_position"]
    if not pos:
        return
        
    pnl = pos["unrealized_pnl"]
    fee = (pos["margin"] * pos["leverage"]) * 0.0005
    final_pnl = round(pnl - fee, 2)
    
    platform_state["balance"] += final_pnl
    platform_state["equity"] = round(platform_state["balance"] + final_pnl, 2)
    platform_state["realized_pnl"] = round(platform_state["realized_pnl"] + final_pnl, 2)
    
    history_record = {
        "time": time.strftime("%I:%M:%S %p"),
        "pair": pos["pair"],
        "side": pos["side"],
        "leverage": f"{pos['leverage']}x",
        "open_price": f"${pos['entry']}",
        "close_price": f"${pos['current_price']}",
        "pnl": f"${final_pnl}" if final_pnl < 0 else f"+${final_pnl}",
        "raw_pnl": final_pnl,
        "trigger": trigger_method
    }
    
    platform_state["trades_history"].insert(0, history_record)
    platform_state["active_position"] = None
    
    log_msg = f"[{trigger_method}]: Closed {pos['pair']} @ ${pos['current_price']} (${final_pnl})"
    platform_state["telemetry"].insert(0, log_msg)
    save_state()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def get_state():
    return jsonify(platform_state)

@app.route('/api/close_position', methods=['POST'])
def api_close_position():
    if platform_state["active_position"]:
        close_trade("MANUAL_CLOSE")
        return jsonify({"status": "success", "message": "Position closed manually."})
    return jsonify({"status": "error", "message": "No active position."})

if __name__ == '__main__':
    t = threading.Thread(target=background_trading_engine, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000)