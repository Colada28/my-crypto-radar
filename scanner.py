import time
import threading

import ccxt
import requests
from flask import Flask

# ---------- ТВОЙ TELEGRAM ----------
TOKEN = "8941415221:AAHX-1F901LYEatcMEBqJFdTE7QpGbp4t88"
CHAT_ID = "-1003959408476"

# ---------- НАСТРОЙКИ РАДАРА ----------
INTERVAL_SEC = 60          # опрос каждые 60 сек
WINDOW_MIN = 5             # окно анализа 5 минут
PUMP_THRESHOLD = 5.0       # памп >= +5%
DUMP_THRESHOLD = -5.0      # дамп <= -5%
MIN_VOLUME_USDT = 50_000   # минимальный объём за окно

# ---------- TELEGRAM ----------
def send(msg: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=5)
    except:
        pass

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
        except Exception:
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

        # фильтр по объёму
        if window_volume * now_price < MIN_VOLUME_USDT:
            continue

        # памп
        if change_pct >= PUMP_THRESHOLD:
            msg = (
                f"🚀 <b>PUMP</b>\n"
                f"Биржа: Binance\n"
                f"Пара: <b>{symbol}</b>\n"
                f"Изм.: <b>+{change_pct:.2f}%</b> за {WINDOW_MIN} мин\n"
                f"Объём: ~{int(window_volume * now_price):,} USDT"
            )
            send(msg)

        # дамп
        elif change_pct <= DUMP_THRESHOLD:
            msg = (
                f"💥 <b>DUMP</b>\n"
                f"Биржа: Binance\n"
                f"Пара: <b>{symbol}</b>\n"
                f"Изм.: <b>{change_pct:.2f}%</b> за {WINDOW_MIN} мин\n"
                f"Объём: ~{int(window_volume * now_price):,} USDT"
            )
            send(msg)

def radar_loop():
    send("✅ Binance радар запущен")
    while True:
        try:
            scan_binance()
        except Exception as e:
            print("Ошибка в radar_loop:", e)
        time.sleep(INTERVAL_SEC)

# ---------- FLASK ДЛЯ RENDER ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    t = threading.Thread(target=radar_loop)
    t.daemon = True
    t.start()

    app.run(host="0.0.0.0", port=10000)
