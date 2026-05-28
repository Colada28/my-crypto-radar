import time
from datetime import datetime
import requests
import telebot
import os
import http.server
import threading

# ==========================================
# --- БЛОК 1: НАСТРОЙКИ ---
# ==========================================

# Твой старый рабочий токен памп-бота
TELEGRAM_TOKEN = "8834450636:AAEC-FohGV3UixvjoFWzYUhi4RWZsd6ZZsg" 
CHAT_ID = "-1003714825454" 

BINGX_URL = "https://open-api.bingx.com/openApi/swap/v2/quote/ticker"
BYBIT_URL = "https://api.bybit.com"

# Настройки фильтров
MIN_VOLUME_24H = 1500000       # Суточный объем от $1.5M
THRESHOLD_PERCENT = 1.5        # Памп/дамп от 1.5% за 15 минут
MIN_LIQ_AMOUNT = 1500          # Ликвидации Bybit от $1500

CHECK_INTERVAL_SECONDS = 60    

# ==========================================
# --- БЛОК 2: ВЕБ-СЕРВЕРА ДЛЯ RENDER ---
# ==========================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
price_history = {}  
last_alerts = {}

def start_simple_http_server():
    port = int(os.environ.get('PORT', 10000))
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
# --- БЛОК 3: ЛОГИКА СТАРЫХ ПАМПОВ И ЛИКВИДАЦИЙ ---
# ==========================================

def get_bingx_tickers():
    try:
        response = requests.get(BINGX_URL, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                return data.get("data", [])
    except Exception as e:
        print(f"Ошибка BingX API: {e}", flush=True)
    return None

def check_bybit_liquidations():
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
            
            if symbol in last_alerts and current_time - last_alerts[symbol] < 60:
                continue
                
            price = float(trade.get("price", 0))
            qty = float(trade.get("size", 0))
            amount_usd = qty * price
            
            if amount_usd >= MIN_LIQ_AMOUNT:
                side = trade.get("side")
                send_liq_alert(symbol, side, amount_usd, price)
                last_alerts[symbol] = current_time
    except Exception as e:
        print(f"Ошибка ликвидаций Bybit: {e}", flush=True)

def send_pump_alert(symbol, change, price, volume):
    emoji = "🟢 ИМПУЛЬС ВВЕРХ 📈" if change > 0 else "🔴 ИМПУЛЬС ВНИЗ 📉"
    formatted_vol = f"${volume/1_000_000:.2f}M"
    
    clean_symbol = symbol.replace("USDT", "").replace("-USDT", "")
    dynamic_link = f"https://www.coinglass.com/tv/BingX_{clean_symbol}USDT"
    
    message = (
        f"{emoji}\n\n"
        f"🔹 **Монета:** #{clean_symbol} (BingX)\n"
        f"📊 **Движение за 15 мин:** {change:+.2f}%\n"
        f"💰 **Цена:** {price:.8f}".rstrip('0').rstrip('.') + "\n"
        f"💰 **Объем 24h:** {formatted_vol}\n\n"
        f"🔗 [График {clean_symbol} на Coinglass]({dynamic_link})"
    )
    try:
        bot.send_message(CHAT_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e: 
        print(f"Ошибка отправки пампа: {e}", flush=True)

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
    except Exception as e: 
        print(f"Ошибка отправки ликвидации: {e}", flush=True)

if __name__ == "__main__":
    print("=== Скринер перезапущен с ликвидациями и старым токеном ===", flush=True)
    
    while True:
        try:
            tickers = get_bingx_tickers()
            if tickers:
                for item in tickers:
                    symbol = item["symbol"]
                    if not symbol.endswith("-USDT"): continue
                    
                    volume = float(item.get("volume24h_quote", item.get("volume24h", 0)))
                    if volume < MIN_VOLUME_24H: continue
                        
                    new_price = float(item["lastPrice"])
                    
                    if symbol not in price_history:
                        price_history[symbol] = []
                    
                    price_history[symbol].append(new_price)
                    
                    if len(price_history[symbol]) >= 15:
                        old_price = price_history[symbol][0]
                        if old_price > 0:
                            price_change = ((new_price - old_price) / old_price) * 100
                            
                            if abs(price_change) >= THRESHOLD_PERCENT:
                                current_time = time.time()
                                if symbol not in last_alerts or current_time - last_alerts[symbol] > 300:
                                    send_pump_alert(symbol, price_change, new_price, volume)
                                    last_alerts[symbol] = current_time
                        
                        price_history[symbol].pop(0)
            
            check_bybit_liquidations()
            
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}", flush=True)
            
        time.sleep(CHECK_INTERVAL_SECONDS)
