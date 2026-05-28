import time
import requests
import threading
import socket
from pybit.unified_trading import HTTP

# ==============================================================================
# НАСТРОЙКИ БОТА (ВРЕМЕННЫЙ ТЕСТ ДЛЯ ПРОВЕРКИ СВЯЗИ)
# ==============================================================================
TOKEN = "8941415221:AAEUvX08QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

LONG_TRIGGER = 0.01       # Срабатывает мгновенно при минимальном изменении
SHORT_TRIGGER = 0.01      
MIN_VOLUME_M = 0.0        # Без фильтра по объему

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 10      
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

# Функция веб-сервера на сокетах, которая отвечает Render в фоновом потоке
def respond_to_render_pings():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind(("0.0.0.0", 10000))
        server_socket.listen(5)
        print("🖥️ Фоновый сокет-сервер запущен на порту 10000")
        
        while True:
            client_sock, addr = server_socket.accept()
            # Читаем запрос от Render, чтобы закрыть соединение корректно
            client_sock.recv(1024) 
            # Отправляем стандартный HTTP ответ 200 OK
            response = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK"
            client_sock.sendall(response)
            client_sock.close()
    except Exception as e:
        print(f"Ошибка сокет-сервера: {e}")

def main_scanner_loop():
    prices_history = {}
    print("🚀 Сканер рынка запущен напрямую в основном потоке!")
    
    # Сразу шлем тестовую отмашку в Телеграм
    send_telegram_message("🤖 Бот успешно запущен на Render! Начинаю форсированный тест связи...")
    
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
                
                prices_history[symbol].append((current_time, current_price))
                prices_history[symbol] = [p for p in prices_history[symbol] if current_time - p[0] <= 300]
                
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
                                f"🟢 *ТЕСТ ПАМП* 📈\n\n"
                                f"🔹 *Монета:* #{clean_symbol}\n"
                                f"📊 *Изменение:* +{price_change:.2f}%\n"
                                f"💰 *Цена:* {current_price}"
                            )
                        else:
                            msg = (
                                f"🔴 *ТЕСТ ДАМП* 📉\n\n"
                                f"🔹 *Монета:* #{clean_symbol}\n"
                                f"📊 *Изменение:* {price_change:.2f}%\n"
                                f"💰 *Цена:* {current_price}"
                            )
                        
                        LAST_SIGNAL_TIMES[symbol] = current_time
                        send_telegram_message(msg)
                        print(f"✅ Тестовый сигнал отправлен по {clean_symbol}")
                        
        time.sleep(10)

if __name__ == "__main__":
    # 1. Запускаем обслуживание пингов Render в изолированном ФОНОВОМ потоке
    render_thread = threading.Thread(target=respond_to_render_pings, daemon=True)
    render_thread.start()
    
    # 2. ОСНОВНОЙ поток полностью отдаем под сканирование Bybit без блокировок
    main_scanner_loop()
    
