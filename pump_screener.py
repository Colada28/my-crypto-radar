import time
import requests
import asyncio
from fastapi import FastAPI

# ТОКЕН СТРОГО ПО СКРИНШОТУ ИЗ BOTFATHER (С ЗАГЛАВНОЙ V)
TOKEN = "8941415221:AAEUVX08QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

# РЕАЛЬНЫЕ РАБОЧИЕ НАСТРОЙКИ СКАНИРОВАНИЯ
LONG_TRIGGER = 1.0       # Памп от +1.0% за 5 минут
SHORT_TRIGGER = -1.0     # Дамп от -1.0% за 5 минут
MIN_VOLUME_M = 0.1       # Объем торгов от 100 000 USDT за 24 часа

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 300    # Кулдаун 5 минут на одну монету

app = FastAPI()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def get_bybit_tickers():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        res = requests.get(url, timeout=5).json()
        if res.get("retCode") == 0:
            return res["result"]["list"]
    except:
        pass
    return []

# Настоящий асинхронный фоновый движок сканера
async def main_scanner_loop():
    print("🚀 Сканер рынка Bybit успешно запущен в фоновом режиме!")
    send_telegram_message("🤖 *Бот-радар успешно запущен на Render (FastAPI)!* Начинаю непрерывный мониторинг фьючерсов...")
    
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
                        send_telegram_message(msg)
                        print(f" Сигнал отправлен по {clean_symbol}")
                        
        await asyncio.sleep(15)

# Стартовая точка для FastAPI, которая запускает задачу сканирования рынка
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(main_scanner_loop())

# Главная страница для прохождения пингов Render
@app.get("/")
def read_root():
    return {"status": "working"}
