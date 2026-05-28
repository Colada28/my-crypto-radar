import time
import requests
import threading
import http.server
import socketserver
from pybit.unified_trading import HTTP

# ==============================================================================
# НАСТРОЙКИ БОТА (ВРЕМЕННЫЙ ТЕСТ ДЛЯ ПРОВЕРКИ СВЯЗИ)
# ==============================================================================
TOKEN = "8941415221:AAEUvX08QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

LONG_TRIGGER = 0.01       # Сигнал сработает при изменении ВСЕГО на +0.01%
SHORT_TRIGGER = 0.01      # Сигнал сработает при изменении ВСЕГО на -0.01%
MIN_VOLUME_M = 0.0        # Фильтр объема полностью отключен

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 10      # Снижаем кулдаун до 10 секунд для теста
# ==============================================================================

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
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def get_bybit_data():
    try:
        response = session.get_tickers(category="linear")
        if response and response.get("retCode") == 0:
            return response["result"]["list"]
    except:
        pass
    return []

def main_scanner_loop():
    # Даем веб-серверу 15 секунд на прохождение всех проверок Render
    time.sleep(15)
    
    prices_history = {}
    print("🚀 Сканер рынка запущен. Начинаю накопление 5-минутной истории...")
    send_telegram_message("🤖 Бот-радар успешно зафиксирован на сервере. Сбор данных начался!")
    
    while True:
        tickers = get_bybit_data()
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
                
                # Добавляем цену с меткой времени
                prices_history[symbol].append((current_time, current_price))
                
                # Удаляем данные старше 5 минут (300 секунд)
                prices_history[symbol] = [p for p in prices_history[symbol] if current_time - p[0] <= 300]
                
                # Берем самую старую цену за 5 минут для вычисления процента
                old_price = prices_history[symbol][0][1]
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
                        coinglass_url = f"https://www.coinglass.com/pro/futures/LiquidationChart/BingX/{clean_symbol}"
                        
                        if is_long:
                            msg = (
                                f"🟢 *ИМПУЛЬС ВВЕРХ* 📈\n\n"
                                f"🔹 *Монета:* #{clean_symbol} (BingX)\n"
                                f"📊 *Изменение за 5м:* +{price_change:.2f}%\n"
                                f"💰 *Цена:* {current_price}\n"
                                f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                                f"🔗 [Открыть график {clean_symbol} на Coinglass]({coinglass_url})"
                            )
                        else:
                            msg = (
                                f"🔴 *ИМПУЛЬС ВНИЗ* 📉\n\n"
                                f"🔹 *Монета:* #{clean_symbol} (BingX)\n"
                                f"📊 *Изменение за 5м:* {price_change:.2f}%\n"
                                f"💰 *Цена:* {current_price}\n"
                                f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                                f"🔗 [Открыть график {clean_symbol} на Coinglass]({coinglass_url})"
                            )
                        
                        LAST_SIGNAL_TIMES[symbol] = current_time
                        send_telegram_message(msg)
                        print(f"✅ Сигнал по {clean_symbol} отправлен!")
                        
        time.sleep(15)

class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        return 

def run_web_server():
    with socketserver.TCPServer(("0.0.0.0", 10000), HealthCheckHandler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    # Запускаем веб-сервер для удержания деплоя в отдельном потоке
    threading.Thread(target=run_web_server, daemon=True).start()
    # Запускаем основной цикл сканирования
    main_scanner_loop()
