import os
import json
import time
import random
import threading
from flask import Flask, render_template, jsonify, request, Response

app = Flask(__name__)

INITIAL_EQUITY = 100.0  # Matches your preferred $100 starting paper deposit
STATE_FILE = "platform_state.json"

def load_state():
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
            "total_trades": 1,
            "wins": 1,
            "losses": 0,
            "win_rate": 100.0,
            "profit_factor": 2.4,
            "gross_profit": 3.44,
            "gross_loss": 0.0
        },
        "agent_performance": {
            "SOL Volatility Scout": {"trades": 0, "pnl": 0.0},
            "BTC Macro Quant Agent": {"trades": 0, "pnl": 0.0},
            "ETH Derivatives Bot": {"trades": 1, "pnl": 3.44},
            "AVAX Breakout Specialist": {"trades": 0, "pnl": 0.0},
            "BNB Liquidity Agent": {"trades": 0, "pnl": 0.0}
        },
        "active_position": {
            "agent": "ETH Derivatives Bot",
            "pair": "ETHUSDT",
            "side": "LONG",
            "leverage": 16,
            "entry": 3337.07,
            "current_price": 3365.56,
            "margin": 25.0,
            "unrealized_pnl": 3.42,
            "pnl_percentage": 13.7,
            "scaled_out": False,
            "time": "12:42:01 PM"
        },
        "trades_history": [],
        "telemetry": [
            "[Technical AI]: RSI(14) oversold bounce + EMA7 crossover detected.",
            "[Risk Agent]: Kelly Criterion position allocation locked at 25% max collateral.",
            "[Quant Brain AI]: Order book depth & volatility metrics calculated.",
            "[ETH Derivatives Bot]: EXECUTED LONG ON ETHUSDT 16x @ $3337.07"
        ],
        "market_prices": {
            "SOLUSDT": 185.86,
            "BTCUSDT": 91863.09,
            "ETHUSDT": 3365.56,
            "AVAXUSDT": 9.78,
            "BNBUSDT": 625.26
        }
    }

def save_state():
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(platform_state, f, indent=4)
    except Exception as e:
        print(f"Warning: Could not save state: {e}")

platform_state = load_state()

agents_registry = [
    {"name": "SOL Volatility Scout", "pair": "SOLUSDT", "bias": "LONG"},
    {"name": "BTC Macro Quant Agent", "pair": "BTCUSDT", "bias": "LONG"},
    {"name": "ETH Derivatives Bot", "pair": "ETHUSDT", "bias": "SHORT"},
    {"name": "AVAX Breakout Specialist", "pair": "AVAXUSDT", "bias": "LONG"},
    {"name": "BNB Liquidity Agent", "pair": "BNBUSDT", "bias": "SHORT"}
]

def background_trading_engine():
    print("Elite trading engine background thread started.")
    while True:
        try:
            time.sleep(2.5)
            for pair in platform_state["market_prices"]:
                fluctuation = random.uniform(-0.004, 0.004)
                platform_state["market_prices"][pair] = round(
                    platform_state["market_prices"][pair] * (1 + fluctuation), 2
                )

            pos = platform_state["active_position"]
            if pos:
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

                if pos["pnl_percentage"] >= 18.0 or pos["pnl_percentage"] <= -10.0:
                    close_trade("TAKE_PROFIT_HIT" if pos["pnl_percentage"] >= 0 else "STOP_LOSS_HIT")
            else:
                agent = random.choice(agents_registry)
                pair = agent["pair"]
                price = platform_state["market_prices"][pair]
                side = agent["bias"]
                leverage = random.choice([10, 16, 20])
                margin = round(platform_state["equity"] * 0.25, 2)

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
                log_msg = f"[{agent['name']}]: EXECUTED {side} ON {pair} {leverage}x @ ${price}"
                platform_state["telemetry"].insert(0, log_msg)

            save_state()
        except Exception as e:
            print(f"Engine Error: {e}")

def close_trade(trigger_method):
    pos = platform_state["active_position"]
    if not pos: return

    pnl = pos["unrealized_pnl"]
    fee = (pos["margin"] * pos["leverage"]) * 0.0005
    final_pnl = round(pnl - fee, 2)

    platform_state["balance"] += final_pnl
    platform_state["equity"] = round(platform_state["balance"], 2)
    platform_state["realized_pnl"] = round(platform_state["realized_pnl"] + final_pnl, 2)

    stats = platform_state["stats"]
    stats["total_trades"] += 1
    if final_pnl > 0:
        stats["wins"] += 1
        stats["gross_profit"] += final_pnl
    else:
        stats["losses"] += 1
        stats["gross_loss"] += abs(final_pnl)

    total_dec = stats["wins"] + stats["losses"]
    stats["win_rate"] = round((stats["wins"] / total_dec * 100), 1)

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
    return jsonify({"status": "error"})

@app.route('/api/export_csv')
def export_csv():
    csv_data = "Time,Pair,Side,Leverage,OpenPrice,ClosePrice,PnL,Trigger\n"
    for h in platform_state["trades_history"]:
        csv_data += f"{h['time']},{h['pair']},{h['side']},{h['leverage']},{h['open_price']},{h['close_price']},{h['raw_pnl']},{h['trigger']}\n"
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=grok_trades.csv"})

if __name__ == '__main__':
    t = threading.Thread(target=background_trading_engine, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000)