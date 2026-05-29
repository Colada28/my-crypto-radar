import time
import requests

# =============== НАСТРОЙКИ ===============

TELEGRAM_TOKEN = "8941415221:AAHX-1F901LYEatcMEBqJFdTE7QpGbp4t88"

# Сейчас один канал на всё. Если сделаешь отдельные – просто поменяй.
CHAT_ID_LONG = "-1003959408476"    # канал для импульсов вверх
CHAT_ID_SHORT = "-1003959408476"   # канал для импульсов вниз
CHAT_ID_ALL = None                 # общий канал (опционально)

LONG_TRIGGER = 3.0                 # % вверх за 5 минут
SHORT_TRIGGER = -3.0               # % вниз за 5 минут
MIN_VOLUME_24H_M = 5.0             # минимум 5M USDT за сутки
MIN_5M_VOLUME_USDT = 20000         # минимум средний объём за 5 минут

SIGNAL_COOLDOWN = 300              # 5 минут защита от спама по одной монете

# =========================================

LAST_SIGNAL_TIMES = {}             # key: exchange:symbol -> last_ts
PRICE_HISTORY = {}                 # key: exchange:symbol -> [(ts, price), ...]


def send_telegram_message(chat_id, text):
    if not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code != 200:
            print(f"[TG ERROR] {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[TG EXCEPTION]: {e}")


def build_coinglass_link(exchange, symbol):
    """
    Формат, как ты прислал:
    https://www.coinglass.com/tv/ru/BingX_TRX-USDT
    """
    base = "https://www.coinglass.com/tv/ru"
    ex_map = {
        "BYBIT": "Bybit",
        "BINANCE": "Binance",
        "BINGX": "BingX",
    }
    ex = ex_map.get(exchange.upper(), exchange)
    if symbol.endswith("USDT"):
        base_sym = symbol[:-4]
        pair = f"{base_sym}-USDT"
    else:
        pair = symbol
    return f"{base}/{ex}_{pair}"


# ================== BYBIT ==================

def get_bybit_tickers():
    res = []
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get("retCode") == 0:
            for t in data["result"]["list"]:
                symbol = t["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                price = float(t["lastPrice"])
                vol_24h_quote = float(t["turnover24h"])  # USDT
                vol_24h_m = vol_24h_quote / 1_000_000
                res.append({
                    "exchange": "BYBIT",
                    "symbol": symbol,
                    "price": price,
                    "volume_24h_m": vol_24h_m,
                    "volume_24h_quote": vol_24h_quote
                })
    except Exception as e:
        print(f"[BYBIT ERROR]: {e}")
    return res


# ================== BINANCE ==================

def get_binance_tickers():
    res = []
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=7)
        data = r.json()
        for t in data:
            symbol = t["symbol"]
            if not symbol.endswith("USDT"):
                continue
            price = float(t["lastPrice"])
            vol_24h_quote = float(t["quoteVolume"])  # USDT
            vol_24h_m = vol_24h_quote / 1_000_000
            res.append({
                "exchange": "BINANCE",
                "symbol": symbol,
                "price": price,
                "volume_24h_m": vol_24h_m,
                "volume_24h_quote": vol_24h_quote
            })
    except Exception as e:
        print(f"[BINANCE ERROR]: {e}")
    return res


# ================== BINGX ==================

def get_bingx_tickers():
    res = []
    try:
        url = "https://open-api.bingx.com/openApi/swap/v2/market/tickers"
        r = requests.get(url, timeout=7)
        data = r.json()

        if isinstance(data, dict):
            if data.get("code") in (0, "0", "00000"):
                tickers = data.get("data") or data.get("ticker") or []
            else:
                tickers = data.get("data") or data.get("ticker") or []
        else:
            tickers = []

        for t in tickers:
            symbol_raw = t.get("symbol") or t.get("symbolName")
            if not symbol_raw:
                continue

            if symbol_raw.endswith("-USDT"):
                norm_symbol = symbol_raw.replace("-USDT", "USDT")
            else:
                norm_symbol = symbol_raw

            if not norm_symbol.endswith("USDT"):
                continue

            price = float(
                t.get("lastPrice")
                or t.get("last")
                or t.get("close")
                or 0
            )
            quote_vol = (
                t.get("quoteVolume")
                or t.get("amount")
                or t.get("turnover")
            )
            if quote_vol is None:
                continue

            vol_24h_quote = float(quote_vol)
            vol_24h_m = vol_24h_quote / 1_000_000

            res.append({
                "exchange": "BINGX",
                "symbol": norm_symbol,
                "price": price,
                "volume_24h_m": vol_24h_m,
                "volume_24h_quote": vol_24h_quote
            })
    except Exception as e:
        print(f"[BINGX ERROR]: {e}")
    return res


# ============ ЛОГИКА ИМПУЛЬСОВ ============

def find_price_5min_ago(history, now_ts):
    target = now_ts - 300
    closest_price = None
    min_diff = 1e9
    for ts, price in history:
        diff = abs(ts - target)
        if diff < min_diff:
            min_diff = diff
            closest_price = price
    return closest_price


def process_ticker(t):
    exchange = t["exchange"]
    symbol = t["symbol"]
    price = t["price"]
    vol_24h_m = t["volume_24h_m"]
    vol_24h_quote = t["volume_24h_quote"]

    if vol_24h_m < MIN_VOLUME_24H_M:
        return

    avg_5m_volume = vol_24h_quote / 288.0
    if avg_5m_volume < MIN_5M_VOLUME_USDT:
        return

    key = f"{exchange}:{symbol}"
    now_ts = time.time()

    if key not in PRICE_HISTORY:
        PRICE_HISTORY[key] = []
    PRICE_HISTORY[key].append((now_ts, price))

    PRICE_HISTORY[key] = [
        (ts, p) for ts, p in PRICE_HISTORY[key] if now_ts - ts <= 360
    ]

    old_price = find_price_5min_ago(PRICE_HISTORY[key], now_ts)
    if not old_price or old_price == 0:
        return

    change_pct = (price - old_price) / old_price * 100

    is_long = change_pct >= LONG_TRIGGER
    is_short = change_pct <= SHORT_TRIGGER

    if not (is_long or is_short):
        return

    last_ts = LAST_SIGNAL_TIMES.get(key)
    if last_ts and (now_ts - last_ts < SIGNAL_COOLDOWN):
        return

    LAST_SIGNAL_TIMES[key] = now_ts

    clean_symbol = symbol.replace("USDT", "")
    coinglass_url = build_coinglass_link(exchange, symbol)

    direction_emoji = "🟢" if is_long else "🔴"
    direction_text = "ИМПУЛЬС ВВЕРХ" if is_long else "ИМПУЛЬС ВНИЗ"

    msg = (
        f"{direction_emoji} *{direction_text}*\n"
        f"🏦 *Биржа:* {exchange}\n"
        f"🔹 *Монета:* #{clean_symbol}\n"
        f"📊 *Изменение за 5м:* {change_pct:.2f}%\n"
        f"💰 *Цена:* {price}\n"
        f"💵 *Объем 24h:* {vol_24h_m:.2f}M USDT\n"
        f"📈 [Coinglass график]({coinglass_url})"
    )

    if is_long:
        send_telegram_message(CHAT_ID_LONG, msg)
    if is_short:
        send_telegram_message(CHAT_ID_SHORT, msg)
    if CHAT_ID_ALL:
        send_telegram_message(CHAT_ID_ALL, msg)

    print(f"[ALERT] {exchange} {symbol} {change_pct:.2f}%")


def main_loop():
    print("🚀 Multi-exchange scanner started...")
    send_telegram_message(CHAT_ID_LONG, "🔥 Бот-радар запущен (LONG/UP сигналы).")
    send_telegram_message(CHAT_ID_SHORT, "🔥 Бот-радар запущен (SHORT/DOWN сигналы).")
    if CHAT_ID_ALL:
        send_telegram_message(CHAT_ID_ALL, "🔥 Бот-радар запущен (общий канал).")

    while True:
        try:
            all_tickers = []
            all_tickers += get_bybit_tickers()
            all_tickers += get_binance_tickers()
            all_tickers += get_bingx_tickers()

            for t in all_tickers:
                process_ticker(t)

        except Exception as e:
            print(f"[MAIN LOOP ERROR]: {e}")

        time.sleep(15)


if __name__ == "__main__":
    main_loop()
