import time
import requests
import http.server
import threading

# НАСТРОЙКИ БОТА
TELEGRAM_TOKEN = "8268691280:AAGhrZbF4okL7Yx08qm1sTXZI7azyQGA4zM"
CHAT_ID = "5354904033"

LONG_TRIGGER = 2.5
SHORT_TRIGGER = 4.0
MIN_VOLUME_M = 0.5
CHAT_ID = "354415600"
# МИНИ-СЕРВЕР ДЛЯ ОБМАНА RENDER (ОТВЕЧАЕТ НА ПОРТ 10000)
class WebPortHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("OK".encode("utf-8"))
    def log_message(self, format, *args):
        return

def start_render_port():
    try:
        server = http.server.HTTPServer(('0.0.0.0', 10000), WebPortHandler)
        server.serve_forever()
    except Exception as e:
        print(f"Ошибка сервера портов: {e}")

# Запуск порта в отдельном независимом потоке
threading.Thread(target=start_render_port, daemon=True).start()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
    except Exception as e:
        print(f"Ошибка Телеграма: {e}")
        return False

print("Проверка связи с Телеграмом...")
send_telegram_message("🚀 Бот-радар Bybit успешно запущен на бесплатном Web Service!")

print("🚀 Сканирование Bybit началось...")
last_prices = {}

while True:
    try:
        response = requests.get("https://api.bybit.com/v5/market/tickers?category=linear").json()
        if response.get("retCode") == 0:
            tickers = response["result"]["list"]
            for t in tickers:
                symbol = t["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                current_price = float(t["lastPrice"])
                volume_24h = float(t["turnover24h"]) / 1_000_000
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
        print(f"Ошибка сканирования: {e}")
    time.sleep(10)
