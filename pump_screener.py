import time
import requests
import http.server
import threading

# НАСТРОЙКИ БОТА
TELEGRAM_TOKEN = "8268691280:AAGhrZbF4okL7Yx08qm1sTXZI7azyQGA4zM"
CHAT_ID = "5354904033"

# Параметры триггеров
LONG_TRIGGER = 2.5   # Изменение цены для Лонга (%)
SHORT_TRIGGER = 4.0  # Изменение цены для Шорта (%)
MIN_VOLUME_M = 0.5   # Минимальный объем в млн USDT (0.5М)

# ВСТРОЕННЫЙ МИНИ ВЕБ-СЕРВЕР ДЛЯ ОБХОДА "СПЯЧКИ" RENDER
class SimplePingHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Бот радар активен и работает!".encode("utf-8"))

    def log_message(self, format, *args):
        return

def run_ping_server():
    server_address = ('0.0.0.0', 10000)
    httpd = http.server.HTTPServer(server_address, SimplePingHandler)
    print("🌐 Внутренний веб-сервер запущен на порту 10000 для cron-job.org")
    httpd.serve_forever()

# Запускаем сервер пинга в фоновом потоке
threading.Thread(target=run_ping_server, daemon=True).start()

# ФУНКЦИИ ТЕЛЕГРАМА И ОТПРАВКИ АЛЕРТОВ
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False

# ОТПРАВКА СТАТУСА ПРИ СТАРТЕ
send_telegram_message(
    "🚀 *Бот-радар Bybit успешно запущен на Render!*\n\n"
    f"🟢 Лонг (3М): +{LONG_TRIGGER}%\n"
    f"🔴 Шорт (30М): +{SHORT_TRIGGER}%\n"
    f"🔷 Мин. объем: {MIN_VOLUME_M}M USDT"
)

# ГЛАВНЫЙ ЦИКЛ СКАНИРОВАНИЯ BYBIT (БЕЗ API КЛЮЧЕЙ)
print("🚀 Сканирование Bybit запущено...")
last_prices = {}

while True:
    try:
        # Получаем данные по всем тикерам через публичный API
        response = requests.get("https://api.bybit.com/v5/market/tickers?category=linear").json()
        if response.get("retCode") == 0:
            tickers = response["result"]["list"]
            
            for t in tickers:
                symbol = t["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                
                current_price = float(t["lastPrice"])
                volume_24h = float(t["turnover24h"]) / 1_000_000  # Переводим в миллионы
                
                if volume_24h < MIN_VOLUME_M:
                    continue
                
                if symbol in last_prices:
                    old_price = last_prices[symbol]
                    price_change = ((current_price - old_price) / old_price) * 100
                    
                    if price_change >= LONG_TRIGGER:
                        send_telegram_message(f"🟢 *Памп!* #{symbol}\n📈 Изменение: +{price_change:.2f}%\n💰 Объем: {volume_24h:.2f}M USDT")
                    elif price_change <= -SHORT_TRIGGER:
                        send_telegram_message(f"🔴 *Дамп!* #{symbol}\n📉 Изменение: {price_change:.2f}%\n💰 Объем: {volume_24h:.2f}M USDT")
                
                last_prices[symbol] = current_price
                
    except Exception as e:
        print(f"Ошибка в цикле сканирования: {e}")
        
    time.sleep(10)  # Пауза 10 секунд между проверками
