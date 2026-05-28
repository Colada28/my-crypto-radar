import time
import requests
import http.server
import socketserver

# ТОКЕН С ЗАГЛАВНОЙ БУКВОЙ И КАНАЛ
TOKEN = "8941415221:AAEUVX08QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

# НАСТРОЙКИ ДЛЯ ТЕСТА СВЯЗИ (Мгновенные сигналы)
LONG_TRIGGER = 0.01       
SHORT_TRIGGER = -0.01     
MIN_VOLUME_M = 0.0        

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 10      

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        print(f"[КОНСОЛЬ] Отправка в ТГ. Статус: {res.status_code}, Ответ: {res.text}")
    except Exception as e:
        print(f"[КОНСОЛЬ Ошибка ТГ]: {e}")

def get_bybit_tickers():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        res = requests.get(url, timeout=5).json()
        if res.get("retCode") == 0:
            return res["result"]["list"]
    except Exception as e:
        print(f"[КОНСОЛЬ Ошибка Bybit]: {e}")
    return []

# Создаем кастомный обработчик запросов, который ПРИ КАЖДОМ пинге от Render выполняет один цикл сканирования рынка
class LiveBotHandler(http.server.BaseHTTPRequestHandler):
    # Хранилище истории цен внутри класса, чтобы данные не стирались при запросах
    prices_history = {}

    def do_GET(self):
        # 1. Отвечаем Render 200 OK, чтобы он видел, что сервис живой и не перезапускал сеть
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
        
        # 2. Сразу выполняем проверку рынка
        print(f"[КОНСОЛЬ] Render прислал пинг в {time.strftime('%H:%M:%S')}. Сканирую рынок...")
        
        tickers = get_bybit_tickers()
        current_time = time.time()
        
        if tickers:
            for ticker in tickers:
                symbol = ticker["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                    
                current_price = float(ticker["lastPrice"])
                volume_24h = float(ticker["turnover24h"]) / 1_000_000 
                
                if symbol not in LiveBotHandler.prices_history:
                    LiveBotHandler.prices_history[symbol] = []
                
                LiveBotHandler.prices_history[symbol].append((current_time, current_price))
                LiveBotHandler.prices_history[symbol] = [p for p in LiveBotHandler.prices_history[symbol] if current_time - p[0] <= 300]
                
                old_price = LiveBotHandler.prices_history[symbol][0][1]
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
                        direction = "🟢 ТЕСТ ИМПУЛЬС ВВЕРХ" if is_long else "🔴 ТЕСТ ИМПУЛЬС ВНИЗ"
                        msg = f"{direction}\nМонета: #{clean_symbol}\nИзменение: {price_change:.2f}%\nЦена: {current_price}"
                        
                        LAST_SIGNAL_TIMES[symbol] = current_time
                        send_telegram_message(msg)

    def log_message(self, format, *args):
        return # Отключаем лишний мусор в логах Render

if __name__ == "__main__":
    print("🚀 Скрипт запущен. Ожидаю завершения настройки сети Render...")
    
    # Отправляем приветственный сигнал, проверяя новый токен
    send_telegram_message("🤖 *Бот обновил конфигурацию!* Ожидаю первый сетевой запрос от сервера.")
    
    # Запускаем сервер на порту 10000. Теперь он работает в один поток.
    # Каждые несколько секунд Render сам шлет сюда GET-запрос, дергая наш код сканирования.
    with socketserver.TCPServer(("0.0.0.0", 10000), LiveBotHandler) as httpd:
        httpd.serve_forever()
