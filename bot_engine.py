import os
import json
import time
import random
import threading
from flask import Flask, render_template, jsonify, request, Response

app = Flask(__name__)

INITIAL_EQUITY = 20.0
STATE_FILE = "platform_state.json"

def load_state():
    # If state file exists, load it; otherwise initialize cleanly in memory
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                print("Successfully loaded existing platform state from disk.")
                return data
        except Exception as e:
            print(f"Error loading state file: {e}")

    return {
        "balance": INITIAL_EQUITY,
        "equity": INITIAL_EQUITY,
        "peak_equity": INITIAL_EQUITY,
        "realized_pnl": 0.0,
        "circuit_breaker_active": False,
        "cooldown_until": 0,
        "consecutive_losses": 0,
        "auto_compound": True,
        "stats": {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": 1.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0
        },
        "agent_performance": {
            "SOL Volatility Scout": {"trades": 0, "pnl": 0.0},
            "BTC Macro Quant Agent": {"trades": 0, "pnl": 0.0},
            "ETH Derivatives Bot": {"trades": 0, "pnl": 0.0},
            "AVAX Breakout Specialist": {"trades": 0, "pnl": 0.0},
            "BNB Liquidity Agent": {"trades": 0, "pnl": 0.0}
        },
        "active_position": None,
        "trades_history": [],
        "telemetry": ["[SYSTEM]: Engine initialized successfully. Ready for live scanning."],
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
        print(f"Warning: Could not save state to disk: {e}")

platform_state = load_state()

agents_registry = [
    {"name": "SOL Volatility Scout", "pair": "SOLUSDT", "bias": "LONG"},
    {"name": "BTC Macro Quant Agent", "pair": "BTCUSDT", "bias": "LONG"},
    {"name": "ETH Derivatives Bot", "pair": "ETHUSDT", "bias": "SHORT"},
    {"name": "AVAX Breakout Specialist", "pair": "AVAXUSDT", "bias": "LONG"},
    {"name": "BNB Liquidity Agent", "pair": "BNBUSDT", "bias": "SHORT"}
]

def background_trading_engine():
    print("Background trading engine thread started.")
    while True:
        try:
            time.sleep(2.0)

            # Fluctuate prices slightly
            for pair in platform_state["market_prices"]:
                fluctuation = random.uniform(-0.003, 0.003)
                platform_state["market_prices"][pair] = round(
                    platform_state["market_prices"][pair] * (1 + fluctuation), 2
                )

            pos = platform_state["active_position"]
            if pos:
                # Update live PnL of active position
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

                # Auto close if profit reaches +12% or loss hits -8% for rapid testing visibility
                if pos["pnl_percentage"] >= 12.0 or pos["pnl_percentage"] <= -8.0:
                    trigger = "AUTO_TAKE_PROFIT" if pos["pnl_percentage"] >= 0 else "AUTO_STOP_LOSS"
                    close_trade(trigger)
            else:
                # Force immediate trade generation if no active position is running
                agent = random.choice(agents_registry)
                pair = agent["pair"]
                price = platform_state["market_prices"][pair]
                side = agent["bias"]
                leverage = random.choice([5, 10, 16])

                margin = round(platform_state["equity"] * 0.25, 2)
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
                    "scaled_out": False,
                    "time": time.strftime("%I:%M:%S %p")
                }

                log_msg = f"[{agent['name']}] EXECUTED {side} on {pair} {leverage}x @ ${price}"
                platform_state["telemetry"].insert(0, log_msg)
                if len(platform_state["telemetry"]) > 30:
                    platform_state["telemetry"].pop()

            save_state()
        except Exception as e:
            print(f"Engine Loop Error: {e}")

def close_trade(trigger_method):
    pos = platform_state["active_position"]
    if not pos: return

    pnl = pos["unrealized_pnl"]
    fee = (pos["margin"] * pos["leverage"]) * 0.0005
    final_pnl = round(pnl - fee, 2)

    platform_state["balance"] += final_pnl
    platform_state["equity"] = round(platform_state["balance"], 2)
    platform_state["realized_pnl"] = round(platform_state["realized_pnl"] + final_pnl, 2)

    # Update stats
    stats = platform_state["stats"]
    stats["total_trades"] += 1
    if final_pnl > 0:
        stats["wins"] += 1
        stats["gross_profit"] += final_pnl
    else:
        stats["losses"] += 1
        stats["gross_loss"] += abs(final_pnl)

    total_dec = stats["wins"] + stats["losses"]
    stats["win_rate"] = round((stats["wins"] / total_dec * 100), 1) if total_dec > 0 else 0.0
    if stats["gross_loss"] > 0:
        stats["profit_factor"] = round(stats["gross_profit"] / stats["gross_loss"], 2)
    else:
        stats["profit_factor"] = round(stats["gross_profit"], 2) if stats["gross_profit"] > 0 else 1.0

    # Agent leaderboard update
    agent_name = pos["agent"]
    if agent_name in platform_state["agent_performance"]:
        platform_state["agent_performance"][agent_name]["trades"] += 1
        platform_state["agent_performance"][agent_name]["pnl"] = round(platform_state["agent_performance"][agent_name]["pnl"] + final_pnl, 2)

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
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "No active position"})

@app.route('/api/reset_circuit_breaker', methods=['POST'])
def api_reset_circuit_breaker():
    platform_state["circuit_breaker_active"] = False
    save_state()
    return jsonify({"status": "success"})

@app.route('/api/export_csv')
def export_csv():
    csv_data = "Time,Pair,Side,Leverage,OpenPrice,ClosePrice,PnL,Trigger\n"
    for h in platform_state["trades_history"]:
        csv_data += f"{h['time']},{h['pair']},{h['side']},{h['leverage']},{h['open_price']},{h['close_price']},{h['raw_pnl']},{h['trigger']}\n"
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=grok_trades_export.csv"})

if __name__ == '__main__':
    t = threading.Thread(target=background_trading_engine, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000)