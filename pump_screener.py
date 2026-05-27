import time
from datetime import datetime
import requests
import telebot

# ==========================================
# --- БЛОК 1: НАСТРОЙКИ (ЗАПОЛНИ ИХ) ---
# ==========================================

# Укажи токен твоего старого бота (Cash Pump Screener) из @BotFather
TELEGRAM_TOKEN = "ЗАМЕНИ_НА_ТОКЕН_СТАРОГО_БОТА" 

# Укажи CHAT ID твоего старого канала (например: -1001234567890)
CHAT_ID = "ЗАМЕНИ_НА_ID_СТАРОГО_КАНАЛА" 

# --- ФИЛЬТРЫ ПРОТИВ СПАМА (Настроены жестко) ---

# Игнорировать монеты с суточным объемом меньше $20,000,000.
# (DEUS со скриншота image_9.png с его $3.35M будет отфильтрован).
MIN_VOLUME_24H = 20000000 

# Триггер пампа/дампа: фиксировать движение ТОЛЬКО более 6% за одну проверку.
# (BABYSARK +1.85% со скриншота image_9.png будет отфильтрован).
THRESHOLD_PERCENT = 6.0 

# Проверять рынок раз в 300 секунд (5 минут). Это кардинально уберет спам.
CHECK_INTERVAL_SECONDS = 300 

# ==========================================
# ==========================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
BINGX_URL = "https://open-api.bingx.com/openApi/swap/v2/quote/ticker"
previous_prices = {}

def get_bingx_tickers():
    """Получает текущие данные по всем парам с BingX"""
    try:
        response = requests.get(BINGX_URL, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                tickers = data.get("data", [])
                result = {}
                for item in tickers:
                    symbol = item["symbol"]
                    if symbol.endswith("-USDT"):
                        clean_symbol = symbol.replace("-USDT", "USDT")
                        result[clean_symbol] = {
                            "price": float(item["lastPrice"]),
                            "volume": float(item["volume24h"]),
                            "change": float(item["priceChangePercent"])
                        }
                return result
    except Exception as e:
        print(f"Ошибка получения данных BingX: {e}", flush=True)
    return None

def send_pump_alert(symbol, change, price, volume):
    """Форматирует и отправляет сообщение о сильном движении"""
    if change > 0:
        emoji = "🟢 БЫСТРЫЙ ПАМП 📈"
        type_text = "Взлет цены!"
    else:
        emoji = "🔴 БЫСТРЫЙ ДАМП 📉"
        type_text = "Сброс цены!"
        
    formatted_vol = f"${volume/1_000_000:.2f}M"
    message = (
        f"{emoji}\n\n"
        f"🔹 **Монета:** #{symbol} (BingX)\n"
        f"📊 **Изменение:** {change:+.2f}%\n"
        f"💰 **Текущая цена:** {price:.8f}".rstrip('0').rstrip('.') + "\n"
        f"💰 **Объем 24h:** {formatted_vol}\n\n"
        f"⚡ **Суть:** {type_text}\n"
        f"🔗 [Анализ графиков Coinglass](https://www.coinglass.com/tv/BingX_{symbol})"
    )
    try:
        bot.send_message(CHAT_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔥 Сигнал по {symbol} отправлен!", flush=True)
    except Exception as e:
        print(f"Ошибка отправки в ТГ: {e}", flush=True)

if __name__ == "__main__":
    print(f"=== Скринер Пампов BingX запущен. Фильтр: {THRESHOLD_PERCENT}%, Объем: ${MIN_VOLUME_24H/1_000_000}M ===", flush=True)
    # Полная тишина при старте. Никаких стартовых сообщений.
    
    tickers = get_bingx_tickers()
    if tickers:
        for symbol, data in tickers.items():
            previous_prices[symbol] = data["price"]
        print(f"База цен инициализирована. Ожидание первой проверки {CHECK_INTERVAL_SECONDS} секунд...", flush=True)
    
    time.sleep(CHECK_INTERVAL_SECONDS)

    while True:
        try:
            current_tickers = get_bingx_tickers()
            if not current_tickers:
                time.sleep(20)
                continue
                
            for symbol, current_data in current_tickers.items():
                if current_data["volume"] < MIN_VOLUME_24H:
                    continue
                    
                if symbol in previous_prices:
                    old_price = previous_prices[symbol]
                    new_price = current_data["price"]
                    
                    if old_price == 0: continue
                    
                    price_change = ((new_price - old_price) / old_price) * 100
                    
                    # Применяем жесткий фильтр по силе движения (6%)
                    if abs(price_change) >= THRESHOLD_PERCENT:
                        send_pump_alert(symbol, price_change, new_price, current_data["volume"])
                
                previous_prices[symbol] = current_data["price"]
                
        except Exception as e:
            print(f"Критическая ошибка цикла: {e}", flush=True)
        time.sleep(CHECK_INTERVAL_SECONDS)
