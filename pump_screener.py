import time
import requests
import socket
from pybit.unified_trading import HTTP

# ==============================================================================
# НАСТРОЙКИ БОТА (Чувствительные для теста)
# ==============================================================================
TOKEN = "8941415221:AAEUvX08QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

LONG_TRIGGER = 1.0       # Тестовый Памп от +1.0%
SHORT_TRIGGER = 1.0      # Тестовый Дамп от -1.5%
MIN_VOLUME_M = 0.1       # Объем торгов от 100 000 USDT

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 300    
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

# 1. Открываем порт для Render сразу, чтобы деплой стал Live
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("0.0.0.0", 10000))
server_socket.listen(5)
server_socket.setblocking(False) # Неблокирующий режим, чтобы цикл не зависал

print("🖥️ Локальный порт 10000 открыт для Render")
send_telegram_message("🚀 Бот успешно запущен на Render! Начинаю сканирование рынка...")

prices_history = {}

# 2. Основной рабочий цикл
while True:
    # Проверяем пинги от Render, чтобы он не закрыл деплой
    try:
        client_sock, addr = server_socket.accept()
        response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
        client_sock.sendall(response)
        client_sock.close()
    except BlockingIOError:
        pass # Нет входящих запросов, идем дальше

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
                    
    time.sleep(10)
