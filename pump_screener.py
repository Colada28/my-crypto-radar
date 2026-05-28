import time
import requests
import http.server
import threading
from pybit.unified_trading import HTTP

# =====================================================================
# НАСТРОЙКИ БОТА
# =====================================================================
API_KEY = ""
API_SECRET = ""
TELEGRAM_TOKEN = "8941415221:AAEUVXO8QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

# Твои оригинальные старые настройки
LONG_TRIGGER = 2.5       # Изменение цены для Лонга (%)
SHORT_TRIGGER = 4.0      # Изменение цены для Шорта (%)
MIN_VOLUME_M = 0.5       # Минимальный объем в млн USDT (0.50M)

# Переменные для веб-страницы статуса
START_TIME = time.time()
LOOP_COUNT = 0

# =====================================================================
# ВСТРОЕННЫЙ ВЕБ-СЕРВЕР ДЛЯ МОНИТОРИНГА СТАТУСА
# =====================================================================
class StatusHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        
        # Считаем время работы
        uptime_sec = int(time.time() - START_TIME)
        uptime_min = uptime_sec // 60
        
        # Формируем простую страницу статуса для вывода в браузер
        html = f"""
        <html>
        <head><title>Bybit Radar Status</title></head>
        <body style="font-family: sans-serif; padding: 20px; background: #121214; color: #e1e1e6;">
            <h2>📊 Bybit Памп-Радар Активен</h2>
            <hr style="border-color: #29292e;">
            <p>⏱ <b>Время работы:</b> {uptime_min} мин ({uptime_sec} сек)</p>
            <p>🔄 <b>Проверено циклов рынка:</b> {LOOP_COUNT}</p>
            <p>🟢 <b>Триггер Лонг:</b> +{LONG_TRIGGER}%</p>
            <p>🔴 <b>Триггер Шорт:</b> -{SHORT_TRIGGER}%</p>
            <p>💰 <b>Мин. Объем монеты:</b> {MIN_VOLUME_M}M USDT</p>
            <p style="color: #04d361;">🟢 Бот стабильно пингуется и отправляет алерты в канал.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        return # Отключаем спам в логи Render при каждом пинге

def run_ping_server():
    server_address = ('0.0.0.0', 10000)
    httpd = http.server.HTTPServer(server_address, StatusHandler)
    print("🌍 Мониторинг статуса запущен на порту 10000", flush=True)
    httpd.serve_forever()

# Фоновый поток для веб-сервера (чтобы не мешал циклу биржи)
threading.Thread(target=run_ping_server, daemon=True).start()

# =====================================================================
# ФУНКЦИЯ ОТПРАВКИ СООБЩЕНИЙ В ТЕЛЕГРАМ
# =====================================================================
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code != 200:
            print(f"Ошибка Telegram API: {res.status_code} {res.text}", flush=True)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}", flush=True)

# Инициализация сессии Bybit (публичные данные)
session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)

# Приветственный пуш в канал при деплое
send_telegram_message("🚀 <b>Бот-радар успешно запущен и встал на дежурство!</b>\nПараметры: Памп +2%, Дамп -3%, Объем > 1M.")

prices_snapshot = {}
last_clear_time = time.time()

print("🚀 Сканирование Bybit началось...", flush=True)

# =====================================================================
# ОСНОВНОЙ РАБОЧИЙ ЦИКЛ (БЫСТРЫЙ И ЛЕГКИЙ)
# =====================================================================
while True:
    try:
        # Раз в час сбрасываем старые цены, чтобы не ловить ложные импульсы
        if time.time() - last_clear_time > 3600:
            prices_snapshot.clear()
            last_clear_time = time.time()
            print("История цен очищена по таймеру.", flush=True)

        # Скачиваем одним запросом весь список контрактов
        tickers = session.get_tickers(category="linear")['result']['list']
        LOOP_COUNT += 1
        
        for ticker in tickers:
            symbol = ticker['symbol']
            if not symbol.endswith('USDT'):
                continue
                
            current_price = float(ticker['lastPrice'])
            turnover_24h = float(ticker['turnover24h']) # Объем торгов в USDT
            
            # Фильтр по минимальному суточному объему (1 млн)
            if turnover_24h < (MIN_VOLUME_M * 1_000_000):
                continue
                
            # Если монеты нет в памяти — сохраняем текущую цену как опорную
            if symbol not in prices_snapshot:
                prices_snapshot[symbol] = current_price
                continue
                
            base_price = prices_snapshot[symbol]
            if base_price == 0:
                continue
                
            # Считаем разницу в процентах
            change = ((current_price - base_price) / base_price) * 100
            clean_symbol = symbol.replace("USDT", "")
            coinglass_link = f"https://www.coinglass.com/tv/BingX_{clean_symbol}USDT"
            
            # Проверка условий на Памп (Вверх)
            if change >= LONG_TRIGGER:
                msg = (
                    f"🟢 <b>ИМПУЛЬС ВВЕРХ 📈</b>\n\n"
                    f"🔹 <b>Монета:</b> #{clean_symbol} (Bybit)\n"
                    f"📊 <b>Изменение:</b> <b>+{change:.2f}%</b>\n"
                    f"💰 <b>Цена:</b> {current_price}\n"
                    f"💰 <b>Объем 24h:</b> {turnover_24h / 1_000_000:.2f}M USDT\n\n"
                    f"🔗 <a href='{coinglass_link}'>График {clean_symbol} на Coinglass</a>"
                )
                send_telegram_message(msg)
                prices_snapshot[symbol] = current_price # Обновляем планку, чтобы не спамить
                
            # Проверка условий на Дамп (Вниз)
            elif change <= -SHORT_TRIGGER:
                msg = (
                    f"🔴 <b>ИМПУЛЬС ВНИЗ 📉</b>\n\n"
                    f"🔹 <b>Монета:</b> #{clean_symbol} (Bybit)\n"
                    f"📊 <b>Изменение:</b> <b>{change:.2f}%</b>\n"
                    f"💰 <b>Цена:</b> {current_price}\n"
                    f"💰 <b>Объем 24h:</b> {turnover_24h / 1_000_000:.2f}M USDT\n\n"
                    f"🔗 <a href='{coinglass_link}'>График {clean_symbol} на Coinglass</a>"
                )
                send_telegram_message(msg)
                prices_snapshot[symbol] = current_price

    except Exception as e:
        print(f"Ошибка в основном цикле радара: {e}", flush=True)
        time.sleep(10)
        
    time.sleep(2) # Четкая пауза 2 секунды между кругами сканирования
