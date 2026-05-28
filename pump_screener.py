import time
import requests
import threading
import http.server
import socketserver

# ИСПРАВЛЕННЫЙ ТОКЕН С ЗАГЛАВНОЙ БУКВОЙ 'V' И ЮЗЕРНЕЙМ КАНАЛА
TOKEN = "8941415221:AAEUVX08QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

# РЕАЛЬНЫЕ РАБОЧИЕ НАСТРОЙКИ СКАНИРОВАНИЯ
LONG_TRIGGER = 1.0       # Памп от +1.0% за 5 минут
SHORT_TRIGGER = -1.0     # Дамп от -1.0% за 5 минут
MIN_VOLUME_M = 0.1       # Объем торгов от 100 000 USDT за 24 часа

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 300    # Запрет повторных сигналов по одной монете на 5 минут

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        print(f"[РЛС] Отправка в ТГ: {res.status_code}")
    except Exception as e:
        print(f"[РЛС Ошибка ТГ]: {e}")

def get_bybit_tickers():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        res = requests.get(url, timeout=5).json()
        if res.get("retCode") == 0:
            return res["result"]["list"]
    except Exception as e:
        print(f"[РЛС Ошибка Bybit]: {e}")
    return []

def main_scanner_loop():
    print("!!! [СИСТЕМА] РЛС Сканер Bybit запущен в основном потоке !!!")
    
    # Стартовая отмашка в канал, чтобы сразу увидеть, что бот ожил
    send_telegram_message("🤖 *Бот-радар успешно запущен на сервере!* Начинаю непрерывный мониторинг рынка фьючерсов Bybit.")
    
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
                
                # Записываем текущую цену с меткой времени
                prices_history[symbol].append((current_time, current_price))
                
                # Очищаем историю, оставляя только последние 5 минут (300 секунд)
                prices_history[symbol] = [p for p in prices_history[symbol] if current_time - p[0] <= 300]
                
                # Берем базовую цену (самую старую точку за 5 минут)
                old_price = prices_history[symbol][0][1]
                if old_price == 0:
                    continue
                    
                price_change = ((current_price - old_price) / old_price) * 100
                
                # Проверка условий объема и изменения цены
                if volume_24h >= MIN_VOLUME_M:
                    is_long = price_change >= LONG_TRIGGER
                    is_short = price_change <= SHORT_TRIGGER
                    
                    if is_long or is_short:
                        # Проверяем кулдаун, чтобы не спамить одной монетой
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
                        print(f"[СИГНАЛ] Отправлено оповещение по {symbol}")
                        
        time.sleep(15)

# Конфигурация веб-сервера для удержания процесса на Render
class QuietHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        return

def run_http_server():
    with socketserver.TCPServer(("0.0.0.0", 10000), QuietHandler) as httpd:
        print("[СЕРВЕР] Внутренний HTTP порт 10000 активен.")
        httpd.serve_forever()

if __name__ == "__main__":
    # Запуск обязательного веб-сервера проверки портов в фоне
    server_thread = threading.Thread(target=run_http_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Основной поток забирает сканер
    main_scanner_loop()
