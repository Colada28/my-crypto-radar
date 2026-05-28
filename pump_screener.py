import time
import requests
import threading
from pybit.unified_trading import HTTP

# ==============================================================================
# НАСТРОЙКИ БОТА
# ==============================================================================
TOKEN = "8941415221:AAEUvX08QacNeWRNVcH_UmfW2GuVOBHW0cg"
CHAT_ID = "@alexey_pump_alerts_new"

LONG_TRIGGER = 1.0       # Для теста снижаем до 1.0%
SHORT_TRIGGER = 1.0      # Для теста снижаем до 1.0%
MIN_VOLUME_M = 0.1       # Объем от 100к USDT

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
    except Exception as e:
        print(f"❌ Ошибка отправки в TG: {e}")

def get_bybit_data():
    try:
        response = session.get_tickers(category="linear")
        if response and response.get("retCode") == 0:
            return response["result"]["list"]
        else:
            print(f"⚠️ API Bybit вернул код ответа: {response.get('retCode') if response else 'None'}")
    except Exception as e:
        print(f"❌ Критическая ошибка API Bybit: {e}")
    return []

def main_scanner_loop():
    prices_history = {} 
    print("🚀 Сканер рынка официально запущен!")
    
    while True:
        tickers = get_bybit_data()
        current_time = time.time()
        
        if not tickers:
            print("⚠️ Не удалось получить тикеры от Bybit. Повтор через 10 сек...")
            time.sleep(10)
            continue
            
        print(f"📊 Проверяю рынок... Получено {len(tickers)} пар от Bybit.")
        
        for ticker in tickers:
            symbol = ticker["symbol"]
            if not symbol.endswith("USDT"):
                continue
                
            current_price = float(ticker["lastPrice"])
            volume_24h = float(ticker["turnover24h"]) / 1_000_000 
            
            if symbol not in prices_history:
                prices_history[symbol] = []
            
            prices_history[symbol].append((current_time, current_price))
            
            # Храним историю за последние 5 минут (300 секунд)
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
                    print(f"✅ Сигнал отправлен в TG по монете {clean_symbol}")
                    
        time.sleep(10)

# ЗАПУСК ПОТОКА
threading.Thread(target=main_scanner_loop, daemon=True).start()

# ВЕБ-ЗАГЛУШКА ДЛЯ RENDER
import http.server
import socketserver

class QuietHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        return

send_telegram_message("🤖 Бот заступил на дежурство. Логирование запущено.")

with socketserver.TCPServer(("0.0.0.0", 10000), QuietHandler) as httpd:
    httpd.serve_forever()
