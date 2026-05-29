import time
import asyncio
import http.client
import urllib.parse
import json
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

# Чистый асинхронный отправщик без библиотеки requests
async def send_telegram_message_async(text):
    try:
        url = f"/bot{TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        })
        headers = {"Content-Type": "application/json"}
        
        loop = asyncio.get_event_loop()
        def do_request():
            conn = http.client.HTTPSConnection("api.telegram.org", timeout=5)
            conn.request("POST", url, body=payload, headers=headers)
            res = conn.getresponse()
            data = res.read()
            conn.close()
            return res.status, data
            
        status, _ = await loop.run_in_executor(None, do_request)
        print(f"[ТГ ЛОГ] Отправка. Статус: {status}")
    except Exception as e:
        print(f"[ТГ ОШИБКА]: {e}")

# Чистый асинхронный заборщик данных с Bybit
async def get_bybit_tickers_async():
    try:
        loop = asyncio.get_event_loop()
        def do_request():
            conn = http.client.HTTPSConnection("api.bybit.com", timeout=5)
            conn.request("GET", "/v5/market/tickers?category=linear")
            res = conn.getresponse()
            data = res.read()
            conn.close()
            return json.loads(data.decode("utf-8"))
            
        result = await loop.run_in_executor(None, do_request)
        if result.get("retCode") == 0:
            return result["result"]["list"]
    except Exception as e:
        print(f"[BYBIT ОШИБКА]: {e}")
    return []

# Настоящий неблокирующий фоновый движок сканера
async def main_scanner_loop():
    print("🚀 [СИСТЕМА] Асинхронный движок радара запущен!")
    await send_telegram_message_async("🤖 *Бот-радар успешно запущен на Render!* Начинаю непрерывный мониторинг фьючерсов Bybit.")
    
    prices_history = {}
    
    while True:
        tickers = await get_bybit_tickers_async()
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
                        await send_telegram_message_async(msg)
                        print(f"[СИГНАЛ] Отправлено оповещение по {clean_symbol}")
                        
        # Самое главное: асинхронная пауза, которая не вешает сервер
        await asyncio.sleep(15)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(main_scanner_loop())

@app.get("/")
async def read_root():
    return {"status": "working"}
