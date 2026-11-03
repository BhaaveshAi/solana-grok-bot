import os
import json
import time
import random
import threading
from flask import Flask, render_template, jsonify, request, Response

app = Flask(__name__)

LIVE_MODE = False  # Set to True when live Binance CCXT API keys are added in Render
INITIAL_EQUITY = 20.0
STATE_FILE = "platform_state.json"
CIRCUIT_BREAKER_MAX_DRAWDOWN = 0.30

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")

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
        print(f"Error saving state: {e}")

platform_state = load_state()

agents_registry = [
    {"name": "SOL Volatility Scout", "pair": "SOLUSDT", "bias": "LONG"},
    {"name": "BTC Macro Quant Agent", "pair": "BTCUSDT", "bias": "LONG"},
    {"name": "ETH Derivatives Bot", "pair": "ETHUSDT", "bias": "SHORT"},
    {"name": "AVAX Breakout Specialist", "pair": "AVAXUSDT", "bias": "LONG"},
    {"name": "BNB Liquidity Agent", "pair": "BNBUSDT", "bias": "SHORT"}
]

def calculate_kelly_margin(equity):
    if equity <= 0: return 1.0
    return max(round(equity * 0.25, 2), 1.0)

def update_performance_stats(pnl, agent_name):
    stats = platform_state["stats"]
    stats["total_trades"] += 1
    
    if agent_name in platform_state["agent_performance"]:
        platform_state["agent_performance"][agent_name]["trades"] += 1
        platform_state["agent_performance"][agent_name]["pnl"] = round(platform_state["agent_performance"][agent_name]["pnl"] + pnl, 2)

    if pnl > 0:
        stats["wins"] += 1
        stats["gross_profit"] += pnl
        platform_state["consecutive_losses"] = 0
    else:
        stats["losses"] += 1
        stats["gross_loss"] += abs(pnl)
        platform_state["consecutive_losses"] += 1
        if platform_state["consecutive_losses"] >= 2:
            platform_state["cooldown_until"] = time.time() + 20
            platform_state["telemetry"].insert(0, "[RISK SYSTEM]: 2 consecutive losses detected. Entering 20s cooling pause.")

    total_dec = stats["wins"] + stats["losses"]
    stats["win_rate"] = round((stats["wins"] / total_dec * 100), 1) if total_dec > 0 else 0.0
    stats["profit_factor"] = round(stats["gross_profit"] / stats["gross_loss"], 2) if stats["gross_loss"] > 0 else (round(stats["gross_profit"], 2) if stats["gross_profit"] > 0 else 1.0)

def background_trading_engine():
    while True:
        try:
            time.sleep(2.5)

            for pair in platform_state["market_prices"]:
                fluctuation = random.uniform(-0.0035, 0.0035)
                platform_state["market_prices"][pair] = round(
                    platform_state["market_prices"][pair] * (1 + fluctuation), 2
                )

            if platform_state["equity"] > platform_state.get("peak_equity", INITIAL_EQUITY):
                platform_state["peak_equity"] = platform_state["equity"]

            drawdown = (platform_state.get("peak_equity", INITIAL_EQUITY) - platform_state["equity"]) / platform_state.get("peak_equity", INITIAL_EQUITY)
            if drawdown >= CIRCUIT_BREAKER_MAX_DRAWDOWN:
                platform_state["circuit_breaker_active"] = True
                if platform_state["active_position"]:
                    close_trade("CIRCUIT_BREAKER_HALT")
                save_state()
                continue

            pos = platform_state["active_position"]
            if pos:
                current_price = platform_state["market_prices"][pos["pair"]]
                entry = pos["entry"]
                leverage = pos["leverage"]
                margin = pos["margin"]

                if pos["side"] == "LONG":
                    pnl_pct = (current_price - entry) / entry
                    if current_price > pos.get("peak_price", entry): pos["peak_price"] = current_price
                else:
                    pnl_pct = (entry - current_price) / entry
                    if current_price < pos.get("peak_price", entry): pos["peak_price"] = current_price

                unrealized = margin * leverage * pnl_pct
                pos["current_price"] = current_price
                pos["unrealized_pnl"] = round(unrealized, 2)
                pos["pnl_percentage"] = round(pnl_pct * 100 * leverage, 2)

                # Partial Profit Scale-Out (+10% gain triggers 50% secure)
                if pos["pnl_percentage"] >= 10.0 and not pos.get("scaled_out", False):
                    pos["scaled_out"] = True
                    half_margin_realized = (pos["margin"] * 0.5) * (pnl_pct * leverage)
                    platform_state["realized_pnl"] = round(platform_state["realized_pnl"] + half_margin_realized, 2)
                    platform_state["balance"] += half_margin_realized
                    pos["margin"] *= 0.5
                    platform_state["telemetry"].insert(0, f"[SCALE-OUT]: Secured 50% partial profit on {pos['pair']} (+${round(half_margin_realized,2)})")

                # Trailing Stop Logic
                if pos["pnl_percentage"] > 5.0:
                    peak = pos.get("peak_price", entry)
                    if pos["side"] == "LONG" and current_price <= peak * (1 - (0.04 / leverage)):
                        close_trade("TRAILING_STOP_LOSS")
                        continue
                    elif pos["side"] == "SHORT" and current_price >= peak * (1 + (0.04 / leverage)):
                        close_trade("TRAILING_STOP_LOSS")
                        continue

                if pos["pnl_percentage"] >= 18.0:
                    close_trade("AUTO_TAKE_PROFIT")
                elif pos["pnl_percentage"] <= -12.0:
                    close_trade("AUTO_STOP_LOSS")

            else:
                if platform_state["circuit_breaker_active"] or time.time() < platform_state.get("cooldown_until", 0):
                    continue

                agent = random.choice(agents_registry)
                pair = agent["pair"]
                price = platform_state["market_prices"][pair]
                side = agent["bias"]
                leverage = random.choice([5, 10, 16]) if price > 1000 else random.choice([10, 16, 20])

                if platform_state["equity"] < 3.0:
                    platform_state["balance"] = INITIAL_EQUITY
                    platform_state["equity"] = INITIAL_EQUITY
                    platform_state["peak_equity"] = INITIAL_EQUITY
                    platform_state["circuit_breaker_active"] = False

                margin = calculate_kelly_margin(platform_state["equity"])

                platform_state["active_position"] = {
                    "agent": agent["name"],
                    "pair": pair,
                    "side": side,
                    "leverage": leverage,
                    "entry": price,
                    "current_price": price,
                    "peak_price": price,
                    "margin": margin,
                    "unrealized_pnl": 0.0,
                    "pnl_percentage": 0.0,
                    "scaled_out": False,
                    "time": time.strftime("%I:%M:%S %p")
                }
                
                log_msg = f"[{agent['name']}]: EXECUTED {side} ON {pair} {leverage}x @ ${price}"
                platform_state["telemetry"].insert(0, log_msg)
                if len(platform_state["telemetry"]) > 35: platform_state["telemetry"].pop()

            save_state()
        except Exception as e:
            print(f"Engine Exception: {e}")

def close_trade(trigger_method):
    pos = platform_state["active_position"]
    if not pos: return

    pnl = pos["unrealized_pnl"]
    fee = (pos["margin"] * pos["leverage"]) * 0.0006  # Real friction simulation
    final_pnl = round(pnl - fee, 2)

    platform_state["balance"] += final_pnl
    if platform_state["auto_compound"]:
        platform_state["equity"] = round(platform_state["balance"], 2)
    else:
        platform_state["equity"] = round(INITIAL_EQUITY + platform_state["realized_pnl"] + final_pnl, 2)

    platform_state["realized_pnl"] = round(platform_state["realized_pnl"] + final_pnl, 2)
    update_performance_stats(final_pnl, pos["agent"])

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
    platform_state["peak_equity"] = platform_state["equity"]
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