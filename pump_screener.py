import time
from datetime import datetime
import requests
import telebot

# ==========================================
# --- БЛОК 1: НАСТРОЙКИ (СДЕЛАНЫ ЖЕСТЧЕ) ---
# ==========================================

# 1. Токен твоего СТАРОГО бота (Cash Pump Screener) из @BotFather
TELEGRAM_TOKEN = "ВСТАВЬ_СЮДА_ТОКЕН_СТАРОГО_БОТА" 

# 2. CHAT ID твоего СТАРОГО канала, куда идет спам
# (Обычно это длинное число с минусом, например, -100XXXXXXXXXX)
CHAT_ID = "ВСТАВЬ_СЮДА_ID_СТАРОГО_КАНАЛА" 

# URL API BingX для получения рыночных данных
BINGX_URL = "https://open-api.bingx.com/openApi/swap/v2/quote/ticker"

# --- ФИЛЬТРЫ ПРОТИВ СПАМА (Настроены для скриншота image_9.png) ---

# Игнорировать монеты с суточным объемом меньше $15,000,000.
# (На скриншоте DEUSUSDT имеет всего $3.35M — он будет отфильтрован).
MIN_VOLUME_24H = 15000000 

# Триггер пампа/дампа: фиксировать движение ТОЛЬКО более 4.5% за одну проверку.
# (На скриншоте BABYSARKUSDT +1.85%, DEUS -4.96%. Будет виден только сильный дамп по DEUS).
THRESHOLD_PERCENT = 4.5 

# Проверять рынок раз в 180 секунд (3 минуты).
# На скриншоте image_9.png проверки идут каждую минуту, это слишком часто.
CHECK_INTERVAL_SECONDS = 180 

# ==========================================
# --- БЛОК 2: ЛОГИКА (НЕ ТРЕБУЕТ ПРАВОК) ---
# ==========================================

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

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
                    if symbol.endswith("-USDT"): # Берем только пары к USDT
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
    
    # Смена оформления в зависимости от типа движения
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
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔥 Сигнал по {symbol} ({change:+.2f}%) отправлен!", flush=True)
    except Exception as e:
        print(f"Ошибка отправки в ТГ: {e}", flush=True)

# Хранилище цен для сравнения
previous_prices = {}

if __name__ == "__main__":
    print(f"=== Скринер Пампов BingX запущен. Фильтр: {THRESHOLD_PERCENT}%, Объем: ${MIN_VOLUME_24H/1_000_000}M ===", flush=True)
    
    # При первом запуске просто запоминаем цены, чтобы не спамить сразу
    tickers = get_bingx_tickers()
    if tickers:
        for symbol, data in tickers.items():
            previous_prices[symbol] = data["price"]
        print(f"База цен инициализирована ({len(previous_prices)} пар). Ожидание первой проверки...", flush=True)
    
    time.sleep(CHECK_INTERVAL_SECONDS)

    while True:
        try:
            current_tickers = get_bingx_tickers()
            if not current_tickers:
                time.sleep(10)
                continue
                
            for symbol, current_data in current_tickers.items():
                # Применяем фильтр по объему ПЕРЕД проверкой цены
                if current_data["volume"] < MIN_VOLUME_24H:
                    continue
                    
                if symbol in previous_prices:
                    old_price = previous_prices[symbol]
                    new_price = current_data["price"]
                    
                    if old_price == 0: continue
                    
                    # Расчет процентного изменения цены за интервал проверки
                    price_change = ((new_price - old_price) / old_price) * 100
                    
                    # Применяем жесткий фильтр по силе движения
                    if abs(price_change) >= THRESHOLD_PERCENT:
                        send_pump_alert(symbol, price_change, new_price, current_data["volume"])
                
                # Обновляем базу цен для следующей проверки
                previous_prices[symbol] = current_data["price"]
                
        except Exception as e:
            print(f"Критическая ошибка цикла: {e}", flush=True)
            
        # Пауза между полными проверками рынка
        time.sleep(CHECK_INTERVAL_SECONDS)
