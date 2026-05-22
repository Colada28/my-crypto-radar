import time
import requests
import http.server
import threading
from pybit.unified_trading import HTTP

# =====================================================================
# НАСТРОЙКИ БОТА (Впиши сюда свои данные заново)
# =====================================================================
API_KEY = "ТВОЙ_API_KEY"
API_SECRET = "ТВОЙ_API_SECRET"
TELEGRAM_TOKEN = "ТВОЙ_ТЕЛЕГРАМ_ТОКЕН"
CHAT_ID = "ТВОЙ_CHAT_ID"

# Параметры триггеров
LONG_TRIGGER = 2.5     # Изменение цены для Лонга (%)
SHORT_TRIGGER = 4.0    # Изменение цены для Шорта (%)
MIN_VOLUME_M = 0.5     # Минимальный объем в млн USDT (0.50M)

# =====================================================================
# ВСТРОЕННЫЙ МИНИ-ВЕБ-СЕРВЕР ДЛЯ ОБХОДА "СПЯЧКИ" RENDER
# =====================================================================
class SimplePingHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Отвечаем кодом 200 OK на любой запрос пинговалки
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Бот-радар активен и работает!".encode("utf-8"))

    def log_message(self, format, *args):
        # Отключаем лишний спам логов запросов в консоль
        return

def run_ping_server():
    server_address = ('0.0.0.0', 10000)
    httpd = http.server.HTTPServer(server_address, SimplePingHandler)
    print("🌍 Внутренний веб-сервер запущен на порту 10000 для cron-job.org")
    httpd.serve_forever()

# Запускаем сервер пинга в фоновом потоке, чтобы он не вешал основной цикл
threading.Thread(target=run_ping_server, daemon=True).start()

# =====================================================================
# ФУНКЦИИ ТЕЛЕГРАМА И ОТПРАВКИ АЛЕРТОВ
# =====================================================================
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

# Инициализация клиента Bybit
session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)

# Отправляем пуш, что бот успешно обновился и встал на дежурство
send_telegram_message("🚀 <b>Бот-радар успешно обновлен в облаке и готов к работе 24/7!</b>\nНе забудь настроить cron-job.org.")

# Хранилище для отслеживания базовых цен
prices_snapshot = {}
last_clear_time = time.time()

print("🚀 ОсновнойBybit-радар запущен и сканирует рынок...")

# =====================================================================
# ОСНОВНОЙ ЦИКЛ СКАНИРОВАНИЯ РЫНКА (РАДАР)
# =====================================================================
while True:
    try:
        # Раз в час очищаем историю старых цен, чтобы не ловить ложные пампы
        if time.time() - last_clear_time > 3600:
            prices_snapshot.clear()
            last_clear_time = time.time()
            print("История цен очищена по таймеру.")

        # Получаем данные по всем бессрочным контрактам USDT
        tickers = session.get_tickers(category="linear")['result']['list']
        
        for ticker in tickers:
            symbol = ticker['symbol']
            if not symbol.endswith('USDT'):
                continue
                
            current_price = float(ticker['lastPrice'])
            volume_24h = float(ticker['volume24h'])
            turnover_24h = float(ticker['turnover24h']) # Объем в USDT
            
            # Фильтр по минимальному объему торгов
            if turnover_24h < (MIN_VOLUME_M * 1_000_000):
                continue
                
            # Если монеты еще нет в памяти, записываем её стартовую цену
            if symbol not in prices_snapshot:
                prices_snapshot[symbol] = current_price
                continue
                
            base_price = prices_snapshot[symbol]
            if base_price == 0:
                continue
                
            # Считаем изменение цены в процентах
            change = ((current_price - base_price) / base_price) * 100
            
            # Проверка условий на Лонг (Памп)
            if change >= LONG_TRIGGER:
                msg = f"🟢 <b>ЛОНГ СИГНАЛ</b>\n" \
                      f"🪙 Монета: <b>{symbol}</b>\n" \
                      f"📈 Изменение: <b>+{change:.2f}%</b>\n" \
                      f"💰 Объем: {turnover_24h / 1_000_000:.2f}M USDT"
                send_telegram_message(msg)
                prices_snapshot[symbol] = current_price # Обновляем планку, чтобы не спамить
                
            # Проверка условий на Шорт (Дамп)
            elif change <= -SHORT_TRIGGER:
                msg = f"🔴 <b>ШОРТ СИГНАЛ</b>\n" \
                      f"🪙 Монета: <b>{symbol}</b>\n" \
                      f"📉 Изменение: <b>{change:.2f}%</b>\n" \
                      f"💰 Объем: {turnover_24h / 1_000_000:.2f}M USDT"
                send_telegram_message(msg)
                prices_snapshot[symbol] = current_price

    except Exception as e:
        print(f"Ошибка в основном цикле радара: {e}")
        time.sleep(10) # Задержка при ошибке сети, чтобы не вешать скрипт
        
    time.sleep(2) # Пауза 2 секунды между кругами сканирования Bybit
