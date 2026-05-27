import time
import requests
import telebot

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8834450636:AAH0vH2ayzopTG2atZEezEa5PWkvKMV_Sxs"
DYNAMIC_CHAT_ID = "354415600"

# Переключаемся на официальный API BingX (Swap/Futures)
BINGX_URL = "https://open-api.bingx.com"

# ФИЛЬТРЫ АЛЕРТОВ
MIN_VOLUME_24H = 1000000  # Фильтр: суточный объем монеты на BingX от $1,000,000
MIN_LIQ_AMOUNT = 3000     # Триггер: рыночный сквиз/ордер от $3,000

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def get_active_bingx_pairs():
    """Получает все деривативные пары с BingX и фильтрует по объему"""
    url = f"{BINGX_URL}/openApi/swap/v2/market/ticker"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            response = res.json()
            if response.get("code") == 0 and "data" in response:
                valid_symbols = {}
                for item in response["data"]:
                    symbol = item.get("symbol")
                    # Нам нужны только фьючерсы к USDT (например, BTC-USDT)
                    if symbol and symbol.endswith("-USDT"):
                        vol_24h = float(item.get("volume", 0)) # Объем в USDT за 24ч
                        if vol_24h >= MIN_VOLUME_24H:
                            valid_symbols[symbol] = {
                                "price": float(item.get("lastPrice", 0)),
                                "vol24h": vol_24h
                            }
                return valid_symbols
    except Exception:
        pass
    return {}

def check_bingx_trades(active_coins):
    """Сканирует последние крупные сделки в реальном времени на BingX"""
    for symbol in list(active_coins.keys()):
        url = f"{BINGX_URL}/openApi/swap/v2/market/trades?symbol={symbol}&limit=10"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code != 200:
                continue
                
            response = res.json()
            if response.get("code") != 0 or not response.get("data"):
                continue
                
            trades = response["data"]
            for trade in trades:
                price = float(trade.get("price", 0))
                qty = float(trade.get("qty", 0))
                amount_usd = qty * price
                
                # Если сделка превышает наш лимит ($3,000)
                if amount_usd >= MIN_LIQ_AMOUNT:
                    # У BingX buy=True означает покупку по маркету (вынос шортов / сильный закуп)
                    # buy=False означает продажу по маркету (вынос лонгов / слив)
                    is_buyer = trade.get("isBuyerMaker", False)
                    side = "BUY" if is_buyer else "SELL"
                    
                    vol24h = active_coins[symbol]["vol24h"]
                    send_alert(symbol, side, amount_usd, price, vol24h)
                    
                    # Защита от спама по одной и той же монете
                    time.sleep(0.5)
                    
        except Exception:
            pass
        # Пауза между запросами к разным монетам, чтобы API BingX не заблокировал
        time.sleep(0.2)

def send_alert(symbol, side, amount_usd, price, vol24h):
    """Форматирует алерты под BingX и отправляет в ТГ"""
    # Красивое имя для отображения (из BTC-USDT делаем BTCUSDT)
    clean_symbol = symbol.replace("-", "")
    
    if side == "SELL":
        emoji = "🩸 **КРУПНЫЙ СБРОС / ЛОНГ-ЛИКВИДАЦИЯ (BingX)** 🩸"
        action = "Маркет-мейкер смыл покупателей. Отскок или В-образный разворот вверх! 🟢"
    else:
        emoji = "🔥 **ИМПУЛЬСНЫЙ ПРОБИЙ / ШОРТ-ЛИКВИДАЦИЯ (BingX)** 🔥"
        action = "Продавцов вынесло по стопам. Потенциальный разворот рынка вниз! 🔴"
        
    message = (
        f"{emoji}\n\n"
        f"🔹 **Монета:** #{clean_symbol}\n"
        f"💵 **Цена исполнения:** {price}\n"
        f"💰 **Объем сквиза:** ${amount_usd:,.2f}\n\n"
        f"📊 **Ликвидность площадки:**\n"
        f"└ Суточный объем BingX: ${vol24h/1_000_000:.1f}M\n\n"
        f"⚡ **Действие:** {action}\n\n"
        f"🔗 [График TradingView](https://ru.tradingview.com/chart/?symbol=BINGX:{clean_symbol})"
    )
    
    try:
        bot.send_message(DYNAMIC_CHAT_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
        print(f"🔥 Сигнал BingX по {clean_symbol} отправлен!", flush=True)
    except Exception as e:
        print(f"Ошибка ТГ: {e}", flush=True)

if __name__ == "__main__":
    print("=== Скринер крупных ордеров BingX успешно запущен ===", flush=True)
    
    try:
        bot.send_message(DYNAMIC_CHAT_ID, "🚀 Бот-радар Крупных Сквизов (BingX) успешно активирован!")
    except Exception as e:
        print(f"Ошибка стартового ТГ: {e}", flush=True)

    while True:
        try:
            active_coins = get_active_bingx_pairs()
            if active_coins:
                check_bingx_trades(active_coins)
        except Exception as e:
            print(f"Ошибка цикла: {e}", flush=True)
        # Интервал проверки всей биржи
        time.sleep(15)
