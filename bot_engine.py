import time
import threading
import requests
from flask import Flask, jsonify

# --- CONFIGURATION & AGENT SETTINGS ---
CHECK_INTERVAL_SEC = 30  
SCORE_THRESHOLD = 70     
MAX_TRADE_ALLOCATION_PCT = 0.08  
STOP_LOSS_PCT = -0.06           
TRAILING_STOP_TRIGGER_PCT = 0.12 

# In-Memory Paper Portfolio State
paper_portfolio = {
    "cash": 1000.0,   
    "positions": {}   
}

log_history = []

# --- AGENT 1: SCOUT ---
def scout_agent():
    url = "https://api.dexscreener.com/latest/dex/search?q=solana"
    try:
        res = requests.get(url, timeout=10).json()
        pairs = res.get("pairs", [])
        scouted = []
        for pair in pairs:
            if pair.get("chainId") != "solana":
                continue
            mcap = pair.get("fdv", 0) or pair.get("marketCap", 0)
            pair_created = pair.get("pairCreatedAt", 0)
            if not pair_created:
                continue
            age_hours = (time.time() * 1000 - pair_created) / (1000 * 3600)
            if 0.5 <= age_hours <= 72 and 300_000 <= mcap <= 20_000_000:
                scouted.append(pair)
        return scouted
    except Exception as e:
        print(f"[SCOUT ERROR] {e}")
        return []

# --- AGENT 2: FILTER ---
def filter_agent(pair):
    token_address = pair["baseToken"]["address"]
    liq = pair.get("liquidity", {}).get("usd", 0)
    vol_1h = pair.get("volume", {}).get("h1", 0)
    price_change_1h = pair.get("priceChange", {}).get("h1", 0)

    if liq < 40_000:
        logger_agent("KILL", token_address, "Liquidity under $40k")
        return False
    if vol_1h < 50_000:
        logger_agent("KILL", token_address, "1h Volume under $50k")
        return False
    if price_change_1h >= 80:
        logger_agent("KILL", token_address, "Already pumped +80% in 1h")
        return False
    return True

# --- AGENT 3: ANALYST ---
def analyst_agent(pair):
    score = 0
    symbol = pair["baseToken"]["symbol"]
    txns = pair.get("txns", {}).get("h1", {})
    buys = txns.get("buys", 0)
    sells = txns.get("sells", 1)
    
    ratio = buys / max(sells, 1)
    if ratio > 2.0: score += 30
    elif ratio > 1.2: score += 20
    elif ratio > 1.0: score += 10

    mcap = pair.get("fdv", 1)
    liq = pair.get("liquidity", {}).get("usd", 0)
    if (liq / max(mcap, 1)) >= 0.15: score += 30
    elif (liq / max(mcap, 1)) >= 0.08: score += 20

    m5_change = pair.get("priceChange", {}).get("m5", 0)
    if 3 <= m5_change <= 25: score += 40
    elif 0 < m5_change < 3: score += 20

    print(f"[ANALYST] Token {symbol} scored: {score}/100")
    return score

# --- AGENT 4: EXECUTOR ---
def executor_agent(pair, score):
    symbol = pair["baseToken"]["symbol"]
    token_address = pair["baseToken"]["address"]
    price = float(pair.get("priceUsd", 0))

    if token_address in paper_portfolio["positions"]:
        return

    trade_amount = paper_portfolio["cash"] * MAX_TRADE_ALLOCATION_PCT
    if trade_amount < 10:
        return

    paper_portfolio["cash"] -= trade_amount
    paper_portfolio["positions"][token_address] = {
        "symbol": symbol,
        "entry_price": price,
        "current_price": price,
        "high_price": price,
        "amount_usd": trade_amount,
        "score": score
    }
    logger_agent("BUY", token_address, f"Bought ${trade_amount:.2f} of {symbol} @ ${price:.6f}")

# --- AGENT 5: RISK ---
def risk_agent():
    to_close = []
    for token_address, pos in paper_portfolio["positions"].items():
        curr_price = pos["current_price"]
        entry_price = pos["entry_price"]
        high_price = pos["high_price"]
        pnl_pct = (curr_price - entry_price) / entry_price
        
        if pnl_pct <= STOP_LOSS_PCT:
            to_close.append((token_address, f"Stop Loss Hit ({pnl_pct*100:.2f}%)"))
            continue
        if (high_price - entry_price) / entry_price >= TRAILING_STOP_TRIGGER_PCT:
            drop_from_high = (high_price - curr_price) / high_price
            if drop_from_high >= 0.05:
                to_close.append((token_address, f"Trailing Stop Hit (+{pnl_pct*100:.2f}%)"))

    for token_address, reason in to_close:
        pos = paper_portfolio["positions"].pop(token_address)
        exit_val = pos["amount_usd"] * (pos["current_price"] / pos["entry_price"])
        paper_portfolio["cash"] += exit_val
        logger_agent("SELL", token_address, f"{pos['symbol']} Closed: {reason}. Cash Return: ${exit_val:.2f}")

# --- AGENT 6: LOGGER ---
def logger_agent(action, token, details):
    log_msg = f"[{action}] Token: {token} | {details}"
    print(f"[LOGGER] {log_msg}")
    log_history.append(log_msg)

# --- ENGINE LOOP ---
def run_desk():
    print("=== Grok Bot Solana Memecoin Desk Active (Paper Mode) ===")
    while True:
        scouted_pairs = scout_agent()
        print(f"[SCOUT] Found {len(scouted_pairs)} pairs matching age/mcap criteria.")
        for pair in scouted_pairs:
            if filter_agent(pair):
                score = analyst_agent(pair)
                if score >= SCORE_THRESHOLD:
                    executor_agent(pair, score)
        risk_agent()
        print(f"--- Available Portfolio Cash: ${paper_portfolio['cash']:.2f} ---\n")
        time.sleep(CHECK_INTERVAL_SEC)

# --- FLASK REST API ---
app = Flask(__name__)

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    return jsonify(paper_portfolio)

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify(log_history[-30:])

if __name__ == "__main__":
    # Start bot loop in a background thread so Flask API can run simultaneously
    bot_thread = threading.Thread(target=run_desk, daemon=True)
    bot_thread.start()
    
    # Run Flask server locally on port 5000
    app.run(host='0.0.0.0', port=5000)