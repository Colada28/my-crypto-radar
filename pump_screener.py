import time
import requests
from pybit.unified_trading import HTTP
from collections import deque
from datetime import datetime

# ------------------- ЖЕСТКИЕ НАСТРОЙКИ -------------------
TELEGRAM_TOKEN = "8268691280:AAGhrZbF4okL7Yx08qm1sTXZI7azyQGA4zM"
TELEGRAM_CHAT_ID = "354415600"
CHECK_INTERVAL = 30        # Проверка каждые 30 секунд

# --- НАСТРОЙКИ ПО УМОЛЧАНИЮ (ИЗМЕНЯЮТСЯ ИЗ ТЕЛЕГРАМА) ---
config = {
    "long_price": 2.5,      # Порог для ЛОНГ сигналов (3 минуты)
    "long_oi": 3.0,
    "short_price": 4.0,     # Порог для ШОРТ сигналов (30 минут)
    "short_oi": 5.0,
    "min_volume": 500000    # Объем от 500k USDT
}

# Таймфреймы (в шагах по 30 секунд)
STEPS_3M = 6
STEPS_30M = 60

# Инициализация API Bybit
session = HTTP(testnet=False)
market_history = {}
last_update_id = 0  

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: 
        requests.post(url, json=payload, timeout=5)
    except: 
        pass

def get_market_snapshot():
    snapshot = {}
    try:
        tickers_response = session.get_tickers(category="linear")
        tickers_list = tickers_response.get("result", {}).get("list", [])
        for ticker in tickers_list:
            symbol = ticker.get("symbol")
            if symbol.endswith("USDT"):
                volume_24h = float(ticker.get("turnover24h", 0))
                last_price = float(ticker.get("lastPrice", 0))
                open_interest = float(ticker.get("openInterest", 0))
                
                if volume_24h >= config["min_volume"] and last_price > 0:
                    snapshot[symbol] = {"price": last_price, "oi": open_interest, "vol": volume_24h}
    except Exception as e: 
        print(f"Ошибка получения данных Bybit: {e}")
    return snapshot

def check_telegram_commands():
    global last_update_id
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 1}
    try:
        response = requests.get(url, params=params, timeout=5).json()
        if "result" in response:
            for update in response["result"]:
                last_update_id = update["update_id"]
                message = update.get("message", {})
                text = message.get("text", "").strip()
                chat_id = str(message.get("chat", {}).get("id", ""))
                
                if chat_id != TELEGRAM_CHAT_ID:
                    continue
                
                if text.startswith("/set_long"):
                    try:
                        val = float(text.split()[1])
                        config["long_price"] = val
                        send_telegram_alert(f"ℹ️ Настройка изменена!\nПорог для *ЛОНГ* (3М) теперь: `+{val}%`")
                    except:
                        send_telegram_alert("⚠️ Ошибка. Пиши: `/set_long 2.5`")
                        
                elif text.startswith("/set_short"):
                    try:
                        val = float(text.split()[1])
                        config["short_price"] = val
                        send_telegram_alert(f"ℹ️ Настройка изменена!\nПорог для *ШОРТ* (30М) теперь: `+{val}%`")
                    except:
                        send_telegram_alert("⚠️ Ошибка. Пиши: `/set_short 5.0`")
                
                elif text.startswith("/set_vol"):
                    try:
                        val = float(text.split()[1])
                        config["min_volume"] = val
                        vol_m = val / 1000000
                        send_telegram_alert(f"ℹ️ Фильтр объема изменен!\nМинимум теперь: `{vol_m:.2f}M USDT`")
                    except:
                        send_telegram_alert("⚠️ Ошибка. Пиши: `/set_vol 500000`")
                        
                elif text == "/status":
                    vol_m = config["min_volume"] / 1000000
                    status_msg = (
                        f"📊 *Текущие настройки радара:*\n\n"
                        f"🟢 Лонг (3М): `+{config['long_price']}%` (OI: >{config['long_oi']}%)\n"
                        f"🔴 Шорт (30М): `+{config['short_price']}%` (OI: >{config['short_oi']}%)\n"
                        f"🔹 Минимальный объем: `{vol_m:.2f}M USDT`"
                    )
                    send_telegram_alert(status_msg)
    except:
        pass

print("🔥 Мульти-радар запущен на рабочем ПК!")
send_telegram_alert("🚀 *Бот-радар успешно перенесен на рабочий ПК и запущен!*")

# --- Бессмертный главный цикл ---
while True:
    try:
        current_time = datetime.now().strftime("%H:%M:%S")
        print(f"[{current_time}] Сканирование рынка...")
        
        check_telegram_commands()
        current_data = get_market_snapshot()
        
        if current_data:
            for symbol, current in current_data.items():
                if symbol not in market_history:
                    market_history[symbol] = deque(maxlen=STEPS_30M)
                
                history = market_history[symbol]
                
                if len(history) > 0:
                    # 1. ЛОНГ (3 МИНУТЫ)
                    idx_3m = -STEPS_3M if len(history) >= STEPS_3M else 0
                    past_3m = history[idx_3m]
                    p_change_3m = ((current["price"] - past_3m["price"]) / past_3m["price"]) * 100
                    oi_change_3m = ((current["oi"] - past_3m["oi"]) / past_3m["oi"]) * 100 if past_3m["oi"] > 0 else 0
                    
                    if p_change_3m >= config["long_price"] and oi_change_3m >= config["long_oi"]:
                        vol_m = current["vol"] / 1000000
                        alert = (
                            f"🟢 *Bybit — ЛОНГ (3М) — #{symbol}*\n"
                            f"📈 *Рост цены:* `+{p_change_3m:.2f}%` (За 3 мин)\n"
                            f"🔥 *Рост OI:* `+{oi_change_3m:.2f}%`\n"
                            f"📊 *Объем:* `{vol_m:.2f}M USDT` | *Цена:* `{current['price']}`"
                        )
                        send_telegram_alert(alert)

                    # 2. ШОРТ (30 МИНУТ)
                    if len(history) == STEPS_30M:
                        past_30m = history[0]
                        p_change_30m = ((current["price"] - past_30m["price"]) / past_30m["price"]) * 100
                        oi_change_30m = ((current["oi"] - past_30m["oi"]) / past_30m["oi"]) * 100 if past_30m["oi"] > 0 else 0
                        
                        if p_change_30m >= config["short_price"] and oi_change_30m >= config["short_oi"]:
                            vol_m = current["vol"] / 1000000
                            alert = (
                                f"🔴 *Bybit — ШОРТ (30М) — #{symbol}*\n"
                                f"📈 *Сильный Памп:* `+{p_change_30m:.2f}%` (За 30 мин)\n"
                                f"🔥 *Рост OI:* `+{oi_change_30m:.2f}%`\n"
                                f"📊 *Объем:* `{vol_m:.2f}M USDT` | *Цена:* `{current['price']}`\n"
                                f"🎯 Натягивает резину под нож!"
                        )
                        send_telegram_alert(alert)
                
                history.append(current)
                
    except Exception as main_error:
        # Если упал интернет или залагал запрос, бот не вылетает, а пишет ошибку в консоль
        print(f"⚠️ Системный сбой цикла: {main_error}. Перезапуск через 10 секунд...")
        time.sleep(10)
        
    time.sleep(CHECK_INTERVAL)