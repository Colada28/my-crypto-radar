import time
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from pybit.unified_trading import HTTP

# ==============================================================================
# НАСТРОЙКИ БОТА (Чувствительные для теста)
# ==============================================================================
TOKEN = "8941415221:AAEUvX08QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

LONG_TRIGGER = 1.0       # Импульс от 1%
SHORT_TRIGGER = 1.0      # Импульс от -1%
MIN_VOLUME_M = 0.1       # Объем от 100k USDT
# ==============================================================================

session = HTTP(testnet=False)

# Глобальное хранилище для цен, чтобы они не стирались между пингами крона
if not 'PRICES_HISTORY' in globals():
    PRICES_HISTORY = {}

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
    except Exception as e:
        print(f"❌ Ошибка отправки в TG: {e}")

def scan_market():
    """Функция вызывается при каждом пинге от Cronjob"""
    global PRICES_HISTORY
    current_time = time.time()
    
    print(f"⏰ Запуск сканирования рынка по сигналу Cronjob: {time.strftime('%X')}")
    
    try:
        response = session.get_tickers(category="linear")
        if not response or response.get("retCode") != 0:
            print("⚠️ Ошибка получения данных от Bybit.")
            return
        tickers = response["result"]["list"]
    except Exception as e:
        print(f"❌ Критическая ошибка Bybit API: {e}")
        return

    print(f"📊 Анализирую {len(tickers)} фьючерсных пар...")
    signals_count = 0

    for ticker in tickers:
        symbol = ticker["symbol"]
        if not symbol.endswith("USDT"):
            continue

        current_price = float(ticker["lastPrice"])
        volume_24h = float(ticker["turnover24h"]) / 1_000_000

        if symbol not in PRICES_HISTORY:
            PRICES_HISTORY[symbol] = current_price
            continue

        old_price = PRICES_HISTORY[symbol]
        if old_price == 0:
            PRICES_HISTORY[symbol] = current_price
            continue

        price_change = ((current_price - old_price) / old_price) * 100

        if volume_24h >= MIN_VOLUME_M:
            is_long = price_change >= LONG_TRIGGER
            is_short = price_change <= -SHORT_TRIGGER

            if is_long or is_short:
                clean_symbol = symbol.replace("USDT", "")
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

                send_telegram_message(msg)
                signals_count += 1
                print(f"✅ Отправлен сигнал по монете: {clean_symbol} ({price_change:.2f}%)")

        # Обновляем цену для следующей проверки крон-задачей
        PRICES_HISTORY[symbol] = current_price

    print(f"🏁 Сканирование завершено. Отправлено сигналов: {signals_count}")


class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # На каждый входящий запрос от Cronjob запускаем сканирование
        scan_market()
        
        # Отдаем Render успешный ответ, чтобы он видел, что сервис работает
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Scan complete")
        
    def log_message(self, format, *args):
        return # Отключаем лишний мусор в логах

# Запуск основного веб-сервера
print("🖥️ Веб-сервер запущен на порту 10000. Ожидание запросов от Крона...")
send_telegram_message("🚀 Бот переведен на триггерную систему. Ждем первый пинг от Крона.")

server = HTTPServer(('0.0.0.0', 10000), WebServerHandler)
server.serve_forever()
