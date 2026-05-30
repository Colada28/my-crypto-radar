# ===== SUPER DEBUG FORCE UPDATE =====
FORCE_ID = "2026-05-30-21-00-MG-ALEXEY-SUPERDEBUG-3"
print("SUPER DEBUG ACTIVE:", FORCE_ID, flush=True)
# ====================================

import time
import threading
import ccxt
import requests
from flask import Flask

# ---------- TELEGRAM ----------
TOKEN = "8885217062:AAFkK53jJdB9i01YhRRzRkhFuZrITKrNw_I"
CHAT_ID = "-1003959408476"

# ---------- НАСТРОЙКИ ----------
INTERVAL_SEC = 60
WINDOW_MIN = 5
PUMP_THRESHOLD = 0.1
DUMP_THRESHOLD = -0.1
MIN_VOLUME_USDT = 1000

# ---------- SUPER DEBUG SEND ----------
def send(msg: str):
    print("SEND() START — FORCE:", FORCE_ID, flush=True)

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        print("POSTING TO TELEGRAM...", flush=True)
        r = requests.post(url, data=data, timeout=3)
        print("POST DONE", flush=True)

        print("=== TELEGRAM DEBUG ===", flush=True)
        print("Status:", r.status_code, flush=True)
        print("Response:", r.text, flush=True)
        print("======================", flush=True)

    except Exception as e:
        print("TELEGRAM EXCEPTION:", str(e), flush=True)

    print("SEND() END", flush=True)

# ---------- BINANCE ----------
binance = ccxt.binance()

def scan_binance():
    try:
        markets = binance.load_markets()
    except Exception as e:
        print("Ошибка load_markets:", e, flush=True)
        return

    symbols = [s for s in markets if s.endswith("/USDT")]

    for symbol in symbols:
        try:
            ohlcv = binance.fetch_ohlcv(symbol, timeframe="5m", limit=12)
        except:
            continue

        if len(ohlcv) < 2:
            continue

        closes = [c[4] for c in ohlcv]
        volumes = [c[5] for c in ohlcv]

        now_price = closes[-1]
        window_candles = max(1, WINDOW_MIN // 5)

        if len(closes) <= window_candles:
            continue

        past_price = closes[-1 - window_candles]
        window_volume = sum(volumes[-window_candles:])

        if past_price == 0:
            continue

        change_pct = (now_price - past_price) / past_price * 100

        if window_volume * now_price < MIN_VOLUME_USDT:
            continue

        if change_pct >= PUMP_THRESHOLD:
            send(f"PUMP {symbol} +{change_pct:.2f}%")
        elif change_pct <= DUMP_THRESHOLD:
            send(f"DUMP {symbol} {change_pct:.2f}%")

# ---------- ПОТОК ----------
def radar_loop():
    print("Radar loop started — SUPER DEBUG:", FORCE_ID, flush=True)
    send("🟢 SUPER DEBUG MODE ACTIVE")
    while True:
        try:
            scan_binance()
        except Exception as e:
            print("Ошибка в radar_loop:", e, flush=True)
        time.sleep(INTERVAL_SEC)

# ---------- FLASK ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "OK — SUPER DEBUG " + FORCE_ID

# ---------- MAIN ----------
if __name__ == "__main__":
    print("MAIN STARTED — SUPER DEBUG:", FORCE_ID, flush=True)
    time.sleep(1)
    t = threading.Thread(target=radar_loop)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=10000)
