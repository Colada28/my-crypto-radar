import time
import asyncio
import json
import urllib.request
import urllib.error
from fastapi import FastAPI

# СВЕЖИЙ ТОКЕН ИЗ СКРИНШОТА 1000112216.JPG
TOKEN = "8941415221:AAFvQ0UbOWkhs7wZk1sZbfadd_35daf9RwE"
CHAT_ID = "@alexey_pump_alerts_new"

# НАСТРОЙКИ ФИЛЬТРАЦИИ
LONG_TRIGGER = 1.0       # Памп от +1.0% за 5 минут
SHORT_TRIGGER = -1.0     # Дамп от -1.0% за 5 минут
MIN_VOLUME_M = 0.1       # Минимальный объем торгов за 24ч (0.1M = 100k USDT)

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 300    

app = FastAPI()

def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }).encode("utf-8")
        
        req = urllib.request.Request(
            url, 
            data=payload, 
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            print(f"[ТГ ЛОГ] Сообщение успешно отправлено! Статус: {status}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"[ТГ ОШИБКА ОТ СЕРВЕРА TELEGRAM]: Код {e.code}, Ответ: {error_body}")
    except Exception as e:
        print(f"[ТГ СИСТЕМНАЯ ОШИБКА]: {e}")

def get_bybit_tickers():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("retCode") == 0:
                return data["result"]["list"]
    except Exception as e:
        print(f"[BYBIT ОШИБКА]: {e}")
    return []

async def main_scanner_loop():
    print("🚀 [СИСТЕМА] Фоновый движок сканера Bybit запущен успешно!")
    await asyncio.sleep(3)
    
    # Стартовый пинг в канал для проверки связи
    send_telegram_message("🤖 *Бот-радар успешно запущен на Render с новым токеном!* Начинаю непрерывный мониторинг рынка.")
    
    prices_history = {}
    
    while True:
        loop = asyncio.get_event_loop()
        tickers = await loop.run_in_executor(None, get_bybit_tickers)
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
                        coinglass_url = f"https://www.coinglass.com/pro/futures/LiquidationChart/BingX/{clean_symbol}"
                        
                        if is_long:
                            msg = (
                                f"🟢 *ИМПУЛЬС ВВЕРХ* 📈\n\n"
                                f"🔹 *Монета:* #{clean_symbol} (BingX)\n"
                                f"📊 *Изменение за 5м:* +{price_change:.2f}%\n"
                                f"💰 *Цена:* {current_price}\n"
                                f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                                f"🔗 [Открыть график на Coinglass]({coinglass_url})"
                            )
                        else:
                            msg = (
                                f"🔴 *ИМПУЛЬС ВНИЗ* 📉\n\n"
                                f"🔹 *Монета:* #{clean_symbol} (BingX)\n"
                                f"📊 *Изменение за 5м:* {price_change:.2f}%\n"
                                f"💰 *Цена:* {current_price}\n"
                                f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                                f"🔗 [Открыть график на Coinglass]({coinglass_url})"
                            )
                        
                        LAST_SIGNAL_TIMES[symbol] = current_time
                        await loop.run_in_executor(None, send_telegram_message, msg)
                        print(f"[СИГНАЛ] Отправлено оповещение по {clean_symbol}")
                        
        await asyncio.sleep(15)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(main_scanner_loop())

@app.get("/")
async def read_root():
    return {"status": "working"}
