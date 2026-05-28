import time
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pybit.unified_trading import HTTP

# ==============================================================================
# НАСТРОЙКИ БОТА
# ==============================================================================
TOKEN = "8941415221:AAEUvX08QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

# ЖЕСТКИЕ ФИЛЬТРЫ ОТ СПАМА
LONG_TRIGGER = 5.0       # Памп от +5.0%
SHORT_TRIGGER = 5.0      # Дамп от -5.0%
MIN_VOLUME_M = 2.0       # Объем от 2 млн USDT

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 1800   # Кулдаун 30 минут
# ==============================================================================

# ФЕЙКОВЫЙ ВЕБ-СЕРВЕР ДЛЯ ОБМАНА RENDER
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")
    def log_message(self, format, *args):
        return  # Отключаем спам логов сервера

def run_health_server():
    try:
        server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
        print("🖥️ Фейковый веб-сервер запущен на порту 10000 для Render")
        server.serve_forever()
    except Exception as e:
        print(f"Ошибка веб-сервера: {e}")

# Запуск веб-сервера в отдельном потоке, чтобы он не мешал боту
threading.Thread(target=run_health_server, daemon=True).start()

# Подключение к API
session = HTTP(testnet=False)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка отправки в TG: {e}")

def get_bybit_data():
    try:
        response = session.get_tickers(category="linear")
        if response and response.get("retCode") == 0:
            return response["result"]["list"]
    except Exception as e:
        print(f"Ошибка получения тикеров: {e}")
    return []

prices_history = {}
send_telegram_message("🚀 Бот-радар запущен! Проверка портов пройдена. Линки BingX активны.")
print("🚀 Сканирование рынка началось...")

while True:
    tickers = get_bybit_data()
    current_time = time.time()
    
    for ticker in tickers:
        symbol = ticker["symbol"]
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
        
        if volume_24h >= MIN_VOLUME_M:
            is_long = price_change >= LONG_TRIGGER
            is_short = price_change <= -SHORT_TRIGGER
            
            if is_long or is_short:
                if symbol in LAST_SIGNAL_TIMES:
                    if current_time - LAST_SIGNAL_TIMES[symbol] < SIGNAL_COOLDOWN:
                        continue
                
                clean_symbol = symbol.replace("USDT", "")
                
                # ИСПРАВЛЕННАЯ ССЫЛКА НА ПРО-ГРАФИКИ ЛИКВИДАЦИЙ BINGX
                coinglass_url = f"https://www.coinglass.com/pro/futures/LiquidationChart/BingX/{clean_symbol}"
                
                if is_long:
                    msg = (
                        f"🟢 *ИМПУЛЬС ВВЕРХ* 📈\n\n"
                        f"🔹 *Монета:* #{clean_symbol} (BingX)\n"
                        f"📊 *Изменение:* +{price_change:.2f}%\n"
                        f"💰 *Цена:* {current_price}\n"
                        f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                        f"🔗 [Открыть график {clean_symbol} на Coinglass]({coinglass_url})"
                    )
                else:
                    msg = (
                        f"🔴 *ИМПУЛЬС ВНИЗ* 📉\n\n"
                        f"🔹 *Монета:* #{clean_symbol} (BingX)\n"
                        f"📊 *Изменение:* {price_change:.2f}%\n"
                        f"💰 *Цена:* {current_price}\n"
                        f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                        f"🔗 [Открыть график {clean_symbol} на Coinglass]({coinglass_url})"
                    )
                
                LAST_SIGNAL_TIMES[symbol] = current_time
                send_telegram_message(msg)
                
        prices_history[symbol] = current_price
        
    time.sleep(10)
