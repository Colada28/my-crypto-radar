import time
from datetime import datetime
import requests
import telebot
import os
import http.server
import threading

# ==========================================
# --- БЛОК 1: НАСТРОЙКИ (ПОД СТОП 2% / ТЕЙК 3-4%) ---
# ==========================================

TELEGRAM_TOKEN = "7294451636:AAH0vH2ayzopTG2atZEezEa5PWkvKMV_Sxs" 
CHAT_ID = "-1003714825454" 
BINGX_URL = "https://open-api.bingx.com/openApi/swap/v2/quote/ticker"

# --- ОБНОВЛЕННЫЕ ФИЛЬТРЫ ДЛЯ АКТИВНОЙ ТОРГОВЛИ ---

# Оставляем монеты с хорошим объемом от $15,000,000, чтобы не лезть в «мертвые» пары
MIN_VOLUME_24H = 15000000 

# Снижаем триггер: ловим движение от 2.8% за 1 минуту (идеально под твой тейк)
THRESHOLD_PERCENT = 2.8 

# Ускоряем проверку рынка: проверяем каждые 60 секунд (вместо 5 минут)
CHECK_INTERVAL_SECONDS = 60 

# ==========================================
# --- БЛОК 2: ЛОГИКА (БЕЗ ИЗМЕНЕНИЙ) ---
# ==========================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
previous_prices = {}

def start_simple_http_server():
    """Запускает простой веб-сервер на порту для деплоя Render."""
    port = int(os.environ.get('PORT', 8080))
    server_address = ('', port)
    class SimpleHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
    print(f"--- Простой веб-сервер запущен на порту {port} для Render ---", flush=True)
    httpd = http.server.HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()

threading.Thread(target=start_simple_http_server, daemon=True).start()

def get_bingx_tickers():
    """Получает текущие данные по всем парам с BingX"""
    try:
        response = requests.get(BINGX_URL, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                tickers = data.get("data", [])
                result = {}
                for item in tickers:
                    symbol = item["symbol"]
                    if symbol.endswith("-USDT"):
                        clean_symbol = symbol.replace("-USDT", "USDT")
                        volume = float(item.get("volume24h", item.get("volume24h_quote", 0)))
                        result[clean_symbol] = {
                            "price": float(item["lastPrice"]),
                            "volume": volume,
                            "change": float(item["priceChangePercent"])
                        }
                return result
    except Exception as e:
        print(f"Ошибка получения данных BingX: {e}", flush=True)
    return None

def send_pump_alert(symbol, change, price, volume):
    """Форматирует и отправляет сообщение с точной ссылкой на Coinglass"""
    if change > 0:
        emoji = "🟢 ИМПУЛЬС ВВЕРХ 📈"
        type_text = "Цена начинает расти!"
    else:
        emoji = "🔴 ИМПУЛЬС ВНИЗ 📉"
        type_text = "Цена начинает падать!"
        
    formatted_vol = f"${volume/1_000_000:.2f}M"
    clean_symbol = symbol.replace("USDT", "")
    
    # Ссылка строго под формат Coinglass для BingX (с USDT на конце)
    dynamic_link = f"https://www.coinglass.com/tv/BingX_{clean_symbol}USDT"
    
    message = (
        f"{emoji}\n\n"
        f"🔹 **Монета:** #{clean_symbol} (BingX)\n"
        f"📊 **Движение за минуту:** {change:+.2f}%\n"
        f"💰 **Текущая цена:** {price:.8f}".rstrip('0').rstrip('.') + "\n"
        f"💰 **Объем 24h:** {formatted_vol}\n\n"
        f"⚡ **Суть:** {type_text}\n"
        f"🔗 [Открыть график {clean_symbol} на Coinglass]({dynamic_link})"
    )
    
    try:
        bot.send_message(CHAT_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔥 Сигнал по {clean_symbol} отправлен!", flush=True)
    except Exception as e:
        print(f"Ошибка отправки в ТГ: {e}", flush=True)

if __name__ == "__main__":
    print(f"=== Скринер Пампов запущен. Триггер: {THRESHOLD_PERCENT}% за {CHECK_INTERVAL_SECONDS}с. Объем: ${MIN_VOLUME_24H/1_000_000}M ===", flush=True)
    
    tickers = get_bingx_tickers()
    if tickers:
        for symbol, data in tickers.items():
            previous_prices[symbol] = data["price"]
        print(f"База цен инициализирована. Ожидание первой быстрой проверки...", flush=True)
    
    time.sleep(CHECK_INTERVAL_SECONDS)

    while True:
        try:
            current_tickers = get_bingx_tickers()
            if not current_tickers:
                time.sleep(5)
                continue
                
            for symbol, current_data in current_tickers.items():
                if current_data["volume"] < MIN_VOLUME_24H:
                    continue
                    
                if symbol in previous_prices:
                    old_price = previous_prices[symbol]
                    new_price = current_data["price"]
                    if old_price == 0: continue
                    
                    price_change = ((new_price - old_price) / old_price) * 100
                    if abs(price_change) >= THRESHOLD_PERCENT:
                        send_pump_alert(symbol, price_change, new_price, current_data["volume"])
                
                previous_prices[symbol] = current_data["price"]
        except Exception as e:
            print(f"Критическая ошибка цикла: {e}", flush=True)
            
        time.sleep(CHECK_INTERVAL_SECONDS)
