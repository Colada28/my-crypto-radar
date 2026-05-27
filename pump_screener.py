import time
import requests
import http.server
import threading

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8268691280:AAGhrZbF4okL7Yx08qm1sTXZI7azyQGA4zM"
CHAT_ID = "354415600" 

LONG_TRIGGER = 1.5   
SHORT_TRIGGER = 1.5  
MIN_VOLUME_M = 1.0   

# ТАЙМАУТ ОТ СПАМА (в секундах): 300 секунд = 5 минут блокировки на повторный алерт по той же монете
ANTISPAM_TIMEOUT = 300 

BINGX_URL = "https://open-api.bingx.com"

# МИНИ-СЕРВЕР ДЛЯ ОБМАНА RENDER
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
        print(f"Ошибка сервера портов: {e}", flush=True)

threading.Thread(target=start_render_port, daemon=True).start()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
    except Exception as e:
        print(f"Ошибка Телеграма: {e}", flush=True)
        return False

print("Проверка связи с Телеграмом...", flush=True)
send_telegram_message("🚀 Обновление: Включена защита от спама (алерт на монету раз в 5 минут)!")

print("🚀 Сканирование BingX продолжается...", flush=True)

last_prices = {}
last_alert_times = {}  # Словарь для хранения времени последнего алерта по каждой монете

while True:
    try:
        res = requests.get(f"{BINGX_URL}/openApi/swap/v2/quote/ticker", timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("code") == 0 and "data" in data:
                tickers = data["data"]
                
                current_time = time.time()
                
                for t in tickers:
                    symbol = t["symbol"] # Например, GUA-USDT
                    if not symbol.endswith("-USDT"):
                        continue
                    
                    current_price = float(t.get("lastPrice", 0))
                    volume_24h = float(t.get("volume", 0)) / 1_000_000
                    
                    if volume_24h < MIN_VOLUME_M:
                        continue
                        
                    clean_symbol = symbol.replace("-", "")
                    
                    if clean_symbol in last_prices:
                        old_price = last_prices[clean_symbol]
                        if old_price <= 0:
                            continue
                            
                        price_change = ((current_price - old_price) / old_price) * 100
                        
                        # Проверяем, сколько времени прошло с момента последнего алерта по этой монете
                        time_since_last_alert = current_time - last_alert_times.get(clean_symbol, 0)
                        
                        # Формируем профессиональную ссылку на Coinglass с твоим шаблоном
                        coinglass_url = f"https://www.coinglass.com/ru/tv/BingX_{symbol}?layout=Alexey"
                        
                        if price_change >= LONG_TRIGGER:
                            # Отправляем только если таймаут прошел
                            if time_since_last_alert > ANTISPAM_TIMEOUT:
                                msg = (
                                    f"🟢 **БЫСТРЫЙ ПАМП** 📈\n\n"
                                    f"🔹 **Монета:** #{clean_symbol} (BingX)\n"
                                    f"📊 **Изменение:** +{price_change:.2f}%\n"
                                    f"💵 **Текущая цена:** {current_price}\n"
                                    f"💰 **Объем 24ч:** ${volume_24h:.2f}M\n\n"
                                    f"🔗 [Анализ графиков Coinglass]({coinglass_url})"
                                )
                                send_telegram_message(msg)
                                last_alert_times[clean_symbol] = current_time # Запоминаем время отправки
                            
                        elif price_change <= -SHORT_TRIGGER:
                            # Отправляем только если таймаут прошел
                            if time_since_last_alert > ANTISPAM_TIMEOUT:
                                msg = (
                                    f"🔴 **БЫСТРЫЙ ДАМП** 📉\n\n"
                                    f"🔹 **Монета:** #{clean_symbol} (BingX)\n"
                                    f"📊 **Изменение:** {price_change:.2f}%\n"
                                    f"💵 **Текущая цена:** {current_price}\n"
                                    f"💰 **Объем 24ч:** ${volume_24h:.2f}M\n\n"
                                    f"🔗 [Анализ графиков Coinglass]({coinglass_url})"
                                )
                                send_telegram_message(msg)
                                last_alert_times[clean_symbol] = current_time # Запоминаем время отправки
                            
                    last_prices[clean_symbol] = current_price
                    
    except Exception as e:
        print(f"Ошибка сканирования BingX: {e}", flush=True)
        
    time.sleep(10)
