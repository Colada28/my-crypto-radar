import time
from datetime import datetime
import requests
import telebot

# --- НАСТРОЙКИ (НАСТРОЕНЫ ДЛЯ ТИШИНЫ) ---

# Токен золотого бота (BingX Global Short Screener) - УЖЕ ПОДСТАВЛЕН
TELEGRAM_TOKEN = "8834450636:AAH0vH2ayzopTG2atZEezEa5PWkvKMV_Sxs"

BYBIT_URL = "https://api.bybit.com"

# НАСТРОЙКИ ФИЛЬТРОВ ЛИКВИДАЦИЙ (СДЕЛАЛИ ЖЕСТЧЕ, ЧТОБЫ УМЕНЬШИТЬ ЧАСТОТУ)
# Бот будет игнорировать монеты с суточным объемом меньше $15,000,000.
# Это уберет шум от мелких, неликвидных монет.
MIN_VOLUME_24H = 15000000 

# Триггер: фиксировать ликвидацию ТОЛЬКО от $10,000 за один ордер (было $3,000).
# Это в 3 раза увеличит жесткость фильтра и кардинально уменьшит количество алертов.
MIN_LIQ_AMOUNT = 10000     

bot = telebot.TeleBot(TELEGRAM_TOKEN)
DYNAMIC_CHAT_ID = None

# Словарь для хранения времени отправки последнего алерта по каждой монете.
# Это защита от спама: бот не пришлет алерт по одной монете чаще, чем раз в 5 минут.
last_alerts = {}
ALERT_COOLDOWN_SECONDS = 300 # Коллдаун 5 минут

def discover_chat_id():
    """Автоматически находит ID канала, где бот состоит в админах"""
    global DYNAMIC_CHAT_ID
    print("🤖 Попытка автоопределения ID канала...", flush=True)
    try:
        # Пытаемся получить ID канала через updates
        updates = bot.get_updates(timeout=5, allowed_updates=["my_chat_member"])
        for update in updates:
            if update.my_chat_member and update.my_chat_member.chat:
                DYNAMIC_CHAT_ID = str(update.my_chat_member.chat.id)
                print(f"✅ Успешно найден ID канала: {DYNAMIC_CHAT_ID} (Имя: {update.my_chat_member.chat.title})", flush=True)
                return
    except Exception as e:
        print(f"ℹ️ Запрос обновлений (это нормально при старте): {e}", flush=True)
    
    # Если автоопределение не сработало, используем жестко прописанный резервный ID твоего канала
    if not DYNAMIC_CHAT_ID:
        DYNAMIC_CHAT_ID = "-1003714825454" 

def get_active_futures():
    """Получает активные пары с Bybit для фильтрации по объему"""
    url = f"{BYBIT_URL}/v5/market/tickers?category=linear"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            response = res.json()
            if response.get("retCode") == 0:
                valid_symbols = {}
                for item in response["result"]["list"]:
                    symbol = item["symbol"]
                    if symbol.endswith("USDT"): # Берем только пары к USDT
                        vol_24h = float(item.get("turnover24h", 0))
                        # Применяем жесткий фильтр по объему
                        if vol_24h >= MIN_VOLUME_24H:
                            valid_symbols[symbol] = {
                                "price": float(item.get("lastPrice", 0)),
                                "vol24h": vol_24h
                            }
                return valid_symbols
    except Exception as e:
        print(f"Ошибка получения объемов Bybit: {e}", flush=True)
    return {}

def check_bybit_liquidations(active_coins):
    """Проверяет последние крупные сделки на Bybit"""
    # Запрашиваем 50 последних крупных сделок
    url = f"{BYBIT_URL}/v5/market/recent-trade?category=linear&baseCoin=USDT&limit=50"
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return

        response = res.json()
        if response.get("retCode") != 0 or not response.get("result", {}).get("list"):
            return
            
        trades = response["result"]["list"]
        
        for trade in trades:
            symbol = trade.get("symbol")
            
            # 1. Сначала фильтруем по объему монеты
            if symbol not in active_coins:
                continue
                
            # 2. Проверяем фильтр анти-спама (коллдаун по монете)
            current_time = time.time()
            if symbol in last_alerts:
                if current_time - last_alerts[symbol] < ALERT_COOLDOWN_SECONDS:
                    # Монета в коллдауне, пропускаем
                    continue
                
            price = float(trade.get("price", 0))
            qty = float(trade.get("size", 0))
            amount_usd = qty * price
            
            # 3. Применяем жесткий фильтр по силе ликвидации ($10,000+)
            if amount_usd >= MIN_LIQ_AMOUNT:
                side = trade.get("side")
                vol24h = active_coins[symbol]["vol24h"]
                
                # Отправляем алерт и запоминаем время
                send_alert(symbol, side, amount_usd, price, vol24h)
                last_alerts[symbol] = current_time # Устанавливаем коллдаун
                time.sleep(1) # Небольшая пауза между алертами
                
    except Exception as e:
        print(f"Ошибка парсинга ленты Bybit: {e}", flush=True)

def send_alert(symbol, side, amount_usd, price, vol24h):
    """Форматирует и отправляет сообщение в Телеграм с динамической ссылкой"""
    global DYNAMIC_CHAT_ID
    if not DYNAMIC_CHAT_ID:
        discover_chat_id() # Если ID еще нет, пробуем найти
        if not DYNAMIC_CHAT_ID: return

    # Смена оформления в зависимости от типа движения
    if side in ["Sell", "SELL"]:
        emoji = "🩸 **КРУПНЫЙ СБРОС / ЛОНГ-ЛИКВИДАЦИЯ** 🩸"
        action = "Маркет-мейкер смыл покупателей. Отскок или В-образный разворот вверх! 🟢"
    else:
        emoji = "🔥 **ИМПУЛЬСНЫЙ ПРОБИЙ / ШОРТ-ЛИКВИДАЦИЯ** 🔥"
        action = "Продавцов вынесло по стопам. Потенциальный разворот рынка вниз! 🔴"
        
    formatted_vol = f"${vol24h/1_000_000:.1f}M"
    
    # --- ФИКС ССЫЛКИ НА TRADINGVIEW ---
    # Мы убрали 'BYBIT:' и 'USDT', оставив только чистый тикер (например, KIN или BTC).
    # Это универсальный формат ссылки, который всегда открывает нужный график на TradingView.
    clean_symbol = symbol.replace("USDT", "")
    
    message = (
        f"{emoji}\n\n"
        f"🔹 **Монета:** #{clean_symbol} (Bybit)\n"
        f"💵 **Цена исполнения:** {price:.8f}".rstrip('0').rstrip('.') + "\n"
        f"💰 **Объем сквиза:** ${amount_usd:,.2f}\n\n"
        f"📊 **Ликвидность площадки:**\n"
        f"└ Суточный объем Bybit: {formatted_vol}\n\n"
        f"⚡ **Действие:** {action}\n\n"
        f"🔗 [Открыть график {clean_symbol} на TradingView](https://ru.tradingview.com/chart/?symbol={clean_symbol})"
    )
    
    try:
        bot.send_message(DYNAMIC_CHAT_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔥 Сигнал крупного сквиза по {clean_symbol} на ${amount_usd:.0f} отправлен!", flush=True)
    except Exception as e:
        print(f"Ошибка отправки в ТГ: {e}", flush=True)

if __name__ == "__main__":
    print("=== Скринер крупных ордеров и сквизов Bybit успешно запущен ===", flush=True)
    
    # Ищем ID канала ОДИН раз при старте
    discover_chat_id()
    
    if DYNAMIC_CHAT_ID:
        try:
            bot.send_message(DYNAMIC_CHAT_ID, "🚀 Бот-радар Крупных Сквизов (Bybit) успешно активирован!")
            print(f"Стартовое сообщение отправлено в чат {DYNAMIC_CHAT_ID}", flush=True)
        except Exception as e:
            print(f"Ошибка отправки стартового ТГ: {e}", flush=True)

    # Запускаем бесконечный цикл сбора данных с жесткими фильтрами
    while True:
        try:
            active_coins = get_active_futures()
            if active_coins:
                check_bybit_liquidations(active_coins)
        except Exception as e:
            print(f"Критическая ошибка цикла: {e}", flush=True)
            time.sleep(30) # При критической ошибке ждем дольше
        time.sleep(10) # Проверка раз в 10 секунд
