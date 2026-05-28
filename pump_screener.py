import time
import requests

# ТОКЕН СТРОГО ПО СКРИНШОТУ ИЗ BOTFATHER (С ЗАГЛАВНОЙ V)
TOKEN = "8941415221:AAEUVX08QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

# ЧУВСТВИТЕЛЬНЫЕ НАСТРОЙКИ ДЛЯ ПРОВЕРКИ СВЯЗИ
LONG_TRIGGER = 0.01       
SHORT_TRIGGER = -0.01     
MIN_VOLUME_M = 0.0        

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 15      

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        print(f"[ТГ ЛОГ] Статус: {res.status_code}, Ответ: {res.text}")
    except Exception as e:
        print(f"[ТГ ОШИБКА]: {e}")

def get_bybit_tickers():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        res = requests.get(url, timeout=5).json()
        if res.get("retCode") == 0:
            return res["result"]["list"]
    except Exception as e:
        print(f"[BYBIT ОШИБКА]: {e}")
    return []

if __name__ == "__main__":
    print("🚀 Фоновый сканер запущен. Отправляю стартовый пинг...")
    send_telegram_message("🤖 *Бот запущен как Background Worker!* Начинаю мгновенный тест каналов связи...")
    
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
                
                if symbol not in prices_history:
                    prices_history[symbol] = []
                
                prices_history[symbol].append((current_time, current_price))
                prices_history[symbol] = [p for p in prices_history[symbol] if current_time - p[0] <= 300]
                
                old_price = prices_history[symbol][0][1]
                if old_price == 0:
                    continue
                    
                price_change = ((current_price - old_price) / old_price) * 100
                
                if volume_24h >= MIN_VOLUME_M:
                    is_long = price_change >= LONG_TRIGGER
                    is_short = price_change <= SHORT_TRIGGER
                    
                    if is_long or is_short:
                        if symbol in LAST_SIGNAL_TIMES:
                            if current_time - LAST_SIGNAL_TIMES[symbol] < SIGNAL_COOLDOWN:
                                continue
                        
                        clean_symbol = symbol.replace("USDT", "")
                        direction = "🟢 ТЕСТ ПАМП" if is_long else "🔴 ТЕСТ ДАМП"
                        msg = f"{direction}\nМонета: #{clean_symbol}\nИзменение: {price_change:.2f}%\nЦена: {current_price}"
                        
                        LAST_SIGNAL_TIMES[symbol] = current_time
                        send_telegram_message(msg)
                        print(f"[УСПЕХ] Отправлен сигнал по {symbol}")
                        
        time.sleep(15)
