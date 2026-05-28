import time
import requests
from pybit.unified_trading import HTTP

# ==========================================
# НАСТРОЙКИ БОТА (Твои старые параметры)
# ==========================================
TOKEN = "7292215286:AAEvW_Jz..." # Твой токен бота (оставь свой из старого файла)
CHAT_ID = "@alexey_pump_alerts_new" # Твой канал

LONG_TRIGGER = 2.5       # Памп от +2.5%
SHORT_TRIGGER = 4.0      # Дамп от -4.0%
MIN_VOLUME_M = 2.0       # Подняли до 2M$, чтобы отсечь спам и мелкий мусор

# Защита от спама: монета не побеспокоит чаще раза в 15 минут
LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 900    # 15 минут в секундах

# Инициализация Bybit (Сервер во Франкфурте, без прокси)
session = HTTP(testnet=False)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"Ошибка Telegram API: {res.status_code} {res.text}")
    except Exception as e:
        print(f"Ошибка отправки в TG: {e}")

def get_bybit_data():
    try:
        # Берем данные с линейных фьючерсов (USDT)
        response = session.get_tickers(category="linear")
        if response and response.get("retCode") == 0:
            return response["result"]["list"]
    except Exception as e:
        print(f"Ошибка получения данных с Bybit: {e}")
    return []

# Хранилище цен для вычисления импульсов
prices_history = {}

print("🤖 Мониторинг статуса запущен на порту 10000")
send_telegram_message("🚀 Бот-радар успешно запущен и встал на дежурство по старым настройкам!")
print("🚀 Сканирование Bybit началось...")

while True:
    tickers = get_bybit_data()
    current_time = time.time()
    
    for ticker in tickers:
        symbol = ticker["symbol"]
        
        # Работаем только с парами к USDT
        if not symbol.endswith("USDT"):
            continue
            
        current_price = float(ticker["lastPrice"])
        # Объем за 24 часа в миллионах долларов
        volume_24h = float(ticker["turnover24h"]) / 1_000_000 
        
        if symbol not in prices_history:
            prices_history[symbol] = current_price
            continue
            
        old_price = prices_history[symbol]
        if old_price == 0:
            continue
            
        # Считаем изменение цены в процентах
        price_change = ((current_price - old_price) / old_price) * 100
        
        # Проверяем базовые фильтры: объём торгов
        if volume_24h >= MIN_VOLUME_M:
            
            # Проверяем условия на Памп или Дамп
            is_long = price_change >= LONG_TRIGGER
            is_short = price_change <= -SHORT_TRIGGER
            
            if is_long or is_short:
                # Жесткая защита от спама: проверяем таймаут монеты
                if symbol in LAST_SIGNAL_TIMES:
                    if current_time - LAST_SIGNAL_TIMES[symbol] < SIGNAL_COOLDOWN:
                        continue # Пропускаем, монета еще "остывает"
                
                # Формируем чистый тикер для ссылки (например: ZBCN)
                clean_symbol = symbol.replace("USDT", "")
                
                # ИСПРАВЛЕННАЯ ССЫЛКА на деривативный график Coinglass
                coinglass_url = f"https://www.coinglass.com/tv/Bybit_{clean_symbol}USDT"
                
                if is_long:
                    msg = (
                        f"🟢 *ИМПУЛЬС ВВЕРХ* 📈\n\n"
                        f"🔹 *Монета:* #{clean_symbol} (Bybit)\n"
                        f"📊 *Изменение:* +{price_change:.2f}%\n"
                        f"💰 *Цена:* {current_price}\n"
                        f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                        f"🔗 [График {clean_symbol} на Coinglass]({coinglass_url})"
                    )
                else:
                    msg = (
                        f"🔴 *ИМПУЛЬС ВНИЗ* 📉\n\n"
                        f"🔹 *Монета:* #{clean_symbol} (Bybit)\n"
                        f"📊 *Изменение:* {price_change:.2f}%\n"
                        f"💰 *Цена:* {current_price}\n"
                        f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                        f"🔗 [График {clean_symbol} на Coinglass]({coinglass_url})"
                    )
                
                # Фиксируем время отправки и пушим в канал
                LAST_SIGNAL_TIMES[symbol] = current_time
                send_telegram_message(msg)
                
        # Обновляем цену для следующего круга проверок
        prices_history[symbol] = current_price
        
    # Пауза между циклами сканирования стакана
    time.sleep(10)
