# ===== DOUBLE FORCE UPDATE =====
FORCE_ID = "2026-05-30-20-55-MG-ALEXEY-DOUBLE-2"
print("DOUBLE FORCE UPDATE ACTIVE:", FORCE_ID)
# ===============================

import time
import threading
import ccxt
import requests
from flask import Flask

# Фейковый импорт для принудительного обновления
try:
    import math as _force_update_trigger
except:
    pass

# ---------- TELEGRAM ----------
TOKEN = "8885217062:AAFkK53jJdB9i01YhRRzRkhFuZrITKrNw_I"
CHAT_ID = "-1003959408476"

# ---------- НАСТРОЙКИ РАДАРА ----------
INTERVAL_SEC = 60
WINDOW_MIN = 5
PUMP_THRESHOLD = 0.1
DUMP_THRESHOLD = -0.1
MIN_VOLUME_USDT = 1000

# ---------- TELEGRAM ОТПРАВКА (ДИАГНОСТИКА) ----------
def send(msg: str):
    print("SEND() CALLED — FORCE:", FORCE_ID)

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        r = requests.post(url, data=data, timeout=10)
        print("=== TELEGRAM DEBUG ===")
        print("Status:", r.status_code)
        print("Response:", r.text)
        print("======================")
    except Exception as e:
        print("Telegram error:", e)

# ---------- BINANCE ----------
binance = ccxt.binance()

def scan_binance():
    try:
        markets = binance.load_markets()
    except Exception as e:
        print("Ошибка load_markets:", e)
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
            send(f"🚀 <b>PUMP</b>\n{symbol}\nИзм.: +{change_pct:.2f}%")
        elif change_pct <= DUMP_THRESHOLD:
            send(f"💥 <b>DUMP</b>\n{symbol}\nИзм.: {change_pct:.2f}%")

# ---------- ПОТОК РАДАРА ----------
def radar_loop():
    print("Radar loop started — DOUBLE FORCE:", FORCE_ID)
    send("🟢 Binance радар запущен (DOUBLE FORCE + диагностика)")
    while True:
        try:
            scan_binance()
        except Exception as e:
            print("Ошибка в radar_loop:", e)
        time.sleep(INTERVAL_SEC)

# ---------- FLASK ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "OK — DOUBLE FORCE " + FORCE_ID

# ---------- ГАРАНТИРОВАННЫЙ ЗАПУСК ----------
if __name__ == "__main__":
    print("MAIN STARTED — FORCE:", FORCE_ID)
    time.sleep(2)
    t = threading.Thread(target=radar_loop)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=10000)
