import time
import requests
from pybit.unified_trading import HTTP

# ==============================================================================
# НАСТРОЙКИ БОТА (Вставь свой токен ниже)
# ==============================================================================
TOKEN = "7292215286:AAEvW_Jz..."  # <-- ВСТАВЬ СЮДА СВОЙ ТОКЕН ВНУТРЬ КАВЫЧЕК
CHAT_ID = "@alexey_pump_alerts_new"

# ЖЕСТКИЕ ФИЛЬТРЫ ОТ СПАМА
LONG_TRIGGER = 5.0       # Ловим сильный Памп только от +5.0%
SHORT_TRIGGER = 5.0      # Ловим сильный Дамп только от -5.0%
MIN_VOLUME_M = 2.0       # Объем торгов за 24 часа строго от 2 млн USDT

# Защита от повторных сигналов (монета засыпает на 30 минут)
LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 1800   # 30 минут в секундах
# ==============================================================================

# Подключение к API (Сервер работает во Франкфурте)
session = HTTP(testnet=False)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False  # Разрешаем красивый предпросмотр графика
    }
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"Ошибка Telegram API: {res.status_code} {res.text}")
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

def get_bybit_data():
    try:
        response = session.get_tickers(category="linear")
        if response and response.get("retCode") == 0:
            return response["result"]["list"]
    except Exception as e:
        print(f"Ошибка получения тикеров: {e}")
    return []

prices_history = {}

print("🤖 Мониторинг статуса запущен на порту 10000")
send_telegram_message("🚀 Бот-радар обновлен! Фильтры зажаты: Импульсы от 5%, перезарядка монеты 30 минут. Графики настроены на BingX.")
print("🚀 Сканирование рынка началось...")

while True:
    tickers = get_bybit_data()
    current_time = time.time()
    
    for ticker in tickers:
        symbol = ticker["symbol"]
        
        # Анализируем фьючерсные контракты к USDT
        if not symbol.endswith("USDT"):
            continue
            
        current_price = float(ticker["lastPrice"])
        volume_24h = float(ticker["turnover24h"]) / 1_000_000 
        
        if symbol not in prices_history:
            prices_history[symbol] = current_price
            continue
            
        old_price = prices_history[symbol]
        if old_price == 0:
            continue
            
        price_change = ((current_price - old_price) / old_price) * 100
        
        # 1. Проверяем фильтр по объему торгов
        if volume_24h >= MIN_VOLUME_M:
            
            # 2. Проверяем новые жесткие условия на Памп или Дамп (от 5%)
            is_long = price_change >= LONG_TRIGGER
            is_short = price_change <= -SHORT_TRIGGER
            
            if is_long or is_short:
                # 3. Проверяем защиту от спама (не чаще чем раз в 30 минут)
                if symbol in LAST_SIGNAL_TIMES:
                    if current_time - LAST_SIGNAL_TIMES[symbol] < SIGNAL_COOLDOWN:
                        continue
                
                clean_symbol = symbol.replace("USDT", "")
                
                # Точная рабочая ссылка на интерфейс Coinglass TV для биржи BingX
                coinglass_url = f"https://www.coinglass.com/tv/BingX_{clean_symbol}USDT"
                
                if is_long:
                    msg = (
                        f"🟢 *ИМПУЛЬС ВВЕРХ* 📈\n\n"
                        f"🔹 *Монета:* #{clean_symbol} (BingX)\n"
                        f"📊 *Изменение:* +{price_change:.2f}%\n"
                        f"💰 *Цена:* {current_price}\n"
                        f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                        f"🔗 [Открыть график {clean_symbol} на Coinglass TV]({coinglass_url})"
                    )
                else:
                    msg = (
                        f"🔴 *ИМПУЛЬС ВНИЗ* 📉\n\n"
                        f"🔹 *Монета:* #{clean_symbol} (BingX)\n"
                        f"📊 *Изменение:* {price_change:.2f}%\n"
                        f"💰 *Цена:* {current_price}\n"
                        f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                        f"🔗 [Открыть график {clean_symbol} на Coinglass TV]({coinglass_url})"
                    )
                
                # Фиксируем время сигнала и отправляем в Telegram
                LAST_SIGNAL_TIMES[symbol] = current_time
                send_telegram_message(msg)
                
        prices_history[symbol] = current_price
        
    time.sleep(10)
