import os
import time
import requests

# Твой токен и проверенный ID канала напрямую
TOKEN = "8941415221:AAHX-1F901LYEatcMEBqJFdTE7QpGbp4t88"
CHAT_ID = "-1003959408476"

# НАСТРОЙКИ ФИЛЬТРАЦИИ МУСОРА
LONG_TRIGGER = 1.0       # Импульс вверх от 1%
SHORT_TRIGGER = -1.0     # Импульс вниз от -1%
MIN_VOLUME_M = 5.0       # Монеты с объемом торгов МЕНЬШЕ 5 млн $ бот будет игнорировать

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 300    # Защита от спама одной монетой (5 минут)

def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code == 200:
            print(f"[ТГ ЛОГ] Аalert отправлен успешно!")
        else:
            print(f"[ТГ ОШИБКА]: Код {r.status_code}, Ответ: {r.text}")
    except Exception as e:
        print(f"[СИСТЕМНАЯ ОШИБКА ТГ]: {e}")

def get_bybit_tickers():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get("retCode") == 0:
            return data["result"]["list"]
    except Exception as e:
        print(f"[BYBIT ОШИБКА]: {e}")
    return []

def main_scanner():
    print("🚀 Сканер Bybit запущен в простом режиме...")
    
    # Сразу шлем тестовый алерт в канал, чтобы проверить связь
    send_telegram_message("🤖 Бот-радар успешно запущен и фильтрует мелкие монеты!")
    
    prices_history = {}
    
    while True:
        tickers = get_bybit_tickers()
        current_time = time.time()
        
        if tickers:
            for ticker in tickers:
                symbol = ticker["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                    
                current_price = float(ticker["lastPrice"])
                volume_24h = float(ticker["turnover24h"]) / 1_000_000 
                
                # Фильтр мелких монет: если объем меньше 5 млн USDT — пропускаем ее
                if volume_24h < MIN_VOLUME_M:
                    continue
                
                if symbol not in prices_history:
                    prices_history[symbol] = []
                
                prices_history[symbol].append((current_time, current_price))
                prices_history[symbol] = [p for p in prices_history[symbol] if current_time - p[0] <= 300]
                
                old_price = prices_history[symbol][0][1]
                if old_price == 0:
                    continue
                    
                price_change = ((current_price - old_price) / old_price) * 100
                
                is_long = price_change >= LONG_TRIGGER
                is_short = price_change <= SHORT_TRIGGER
                
                if is_long or is_short:
                    if symbol in LAST_SIGNAL_TIMES:
                        if current_time - LAST_SIGNAL_TIMES[symbol] < SIGNAL_COOLDOWN:
                            continue
                    
                    clean_symbol = symbol.replace("USDT", "")
                    
                    if is_long:
                        msg = (
                            f"🟢 *ИМПУЛЬС ВВЕРХ*\n"
                            f"🔹 *Монета:* #{clean_symbol}\n"
                            f"📊 *Изменение за 5м:* +{price_change:.2f}%\n"
                            f"💰 *Цена:* {current_price}\n"
                            f"💵 *Объем 24h:* {volume_24h:.2f}M USDT"
                        )
                    else:
                        msg = (
                            f"🔴 *ИМПУЛЬС ВНИЗ*\n"
                            f"🔹 *Монета:* #{clean_symbol}\n"
                            f"📊 *Изменение за 5м:* {price_change:.2f}%\n"
                            f"💰 *Цена:* {current_price}\n"
                            f"💵 *Объем 24h:* {volume_24h:.2f}M USDT"
                        )
                    
                    LAST_SIGNAL_TIMES[symbol] = current_time
                    send_telegram_message(msg)
                    print(f"[СИГНАЛ] Отправлен алерт по {clean_symbol}")
                    
        time.sleep(15)

if __name__ == "__main__":
    main_scanner()
