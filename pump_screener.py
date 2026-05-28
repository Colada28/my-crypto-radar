import time
from datetime import datetime
import requests
import telebot
import os
import http.server
import threading

# ==========================================
# --- БЛОК 1: НАСТРОЙКИ (ВСЁ ВКЛЮЧЕНО) ---
# ==========================================

TELEGRAM_TOKEN = "7294451636:AAH0vH2ayzopTG2atZEezEa5PWkvKMV_Sxs" 
CHAT_ID = "-1003714825454" 

BINGX_URL = "https://open-api.bingx.com/openApi/swap/v2/quote/ticker"
BYBIT_URL = "https://api.bybit.com"

# --- МЯГКИЕ ФИЛЬТРЫ ДЛЯ ЧАСТЫХ СИГНАЛОВ ---
MIN_VOLUME_24H = 5000000      # Снизили до $5M (поймает гораздо больше монет)
THRESHOLD_PERCENT = 2.5       # Импульс от 2.5% 
MIN_LIQ_AMOUNT = 5000         # Ликвидации от $5,000 (вместо $10k)

CHECK_INTERVAL_SECONDS = 120  # Проверка каждые 2 минуты (оптимально для API)

# ==========================================
# --- БЛОК 2: ЗАПУСК ВЕБ-СЕРВЕРА ДЛЯ RENDER ---
# ==========================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
previous_prices = {}
last_alerts = {}

def start_simple_http_server():
    port = int(os.environ.get('PORT', 8080))
    server_address = ('', port)
    class SimpleHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
    httpd = http.server.HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()

threading.Thread(target=start_simple_http_server, daemon=True).start()

# ==========================================
# --- БЛОК 3: ЛОГИКА СKРИНЕРОВ ---
# ==========================================

def get_bingx_tickers():
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
                            "volume": volume
                        }
                return result
    except Exception as e:
        print(f"Ошибка BingX API: {e}", flush=True)
    return None

def check_bybit_liquidations():
    """Проверяет крупные ликвидации на Bybit"""
    url = f"{BYBIT_URL}/v5/market/recent-trade?category=linear&baseCoin=USDT&limit=50"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return
        response = res.json()
        if response.get("retCode") != 0 or not response.get("result", {}).get("list"): return
            
        trades = response["result"]["list"]
        for trade in trades:
            symbol = trade.get("symbol")
            current_time = time.time()
            
            if symbol in last_alerts and current_time - last_alerts[symbol] < 120:
                continue
                
            price = float(trade.get("price", 0))
            qty = float(trade.get("size", 0))
            amount_usd = qty * price
            
            if amount_usd >= MIN_LIQ_AMOUNT:
                side = trade.get("side")
                send_liq_alert(symbol, side, amount_usd, price)
                last_alerts[symbol] = current_time
    except Exception as e:
        print(f"Ошибка ликв Bybit: {e}", flush=True)

def send_pump_alert(symbol, change, price, volume):
    emoji = "🟢 ИМПУЛЬС ВВЕРХ 📈" if change > 0 else "🔴 ИМПУЛЬС ВНИЗ 📉"
    formatted_vol = f"${volume/1_000_000:.2f}M"
    clean_symbol = symbol.replace("USDT", "")
    dynamic_link = f"https://www.coinglass.com/tv/BingX_{clean_symbol}USDT"
    
    message = (
        f"{emoji}\n\n"
        f"🔹 **Монета:** #{clean_symbol} (BingX)\n"
        f"📊 **Движение:** {change:+.2f}%\n"
        f"💰 **Цена:** {price:.8f}".rstrip('0').rstrip('.') + "\n"
        f"💰 **Объем 24h:** {formatted_vol}\n\n"
        f"🔗 [График {clean_symbol} на Coinglass]({dynamic_link})"
    )
    try:
        bot.send_message(CHAT_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e: print(f"Ошибка ТГ: {e}")

def send_liq_alert(symbol, side, amount_usd, price):
    emoji = "🩸 ЛОНГ ЛИКВИДАЦИЯ 🩸" if side.lower() == "sell" else "🔥 ШОРТ ЛИКВИДАЦИЯ 🔥"
    clean_symbol = symbol.replace("USDT", "")
    dynamic_link = f"https://www.coinglass.com/tv/BingX_{clean_symbol}USDT"
    
    message = (
        f"{emoji}\n\n"
        f"🔹 **Монета:** #{clean_symbol} (Bybit)\n"
        f"💰 **Объем сквиза:** ${amount_usd:,.2f}\n"
        f"💵 **Цена:** {price:.8f}".rstrip('0').rstrip('.') + "\n\n"
        f"🔗 [График {clean_symbol} на Coinglass]({dynamic_link})"
    )
    try:
        bot.send_message(CHAT_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e: print(f"Ошибка ТГ ликв: {e}")

if __name__ == "__main__":
    print("=== Единый Скринер (Пампы + Ликвидации) запущен ===", flush=True)
    
    tickers = get_bingx_tickers()
    if tickers:
        for symbol, data in tickers.items():
            previous_prices[symbol] = data["price"]
            
    while True:
        try:
            # 1. Проверка Пампов (BingX)
            current_tickers = get_bingx_tickers()
            if current_tickers:
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
            
            # 2. Проверка Ликвидаций (Bybit)
            check_bybit_liquidations()
            
        except Exception as e:
            print(f"Критическая ошибка: {e}", flush=True)
            
        time.sleep(CHECK_INTERVAL_SECONDS)
