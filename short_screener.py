import time
from datetime import datetime
import requests
import telebot

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8834450636:AAH0vH2ayzopTG2atZEezEa5PWkvKMV_Sxs"
CHAT_ID = "-1003714825454"

BINGX_URL = "https://open-api.bingx.com"

# МИНИМАЛЬНЫЙ ПОРОГ ЛИКВИДНОСТИ (Защита от мусора и накруток маркетмейкеров)
MIN_VOLUME_24H = 5000000  # Монета должна иметь от $5,000,000 объема за сутки
MIN_LIQ_AMOUNT = 15000    # Триггер: ликвидация от $15,000 за одну свечу (можно настроить под себя)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def get_active_futures():
    """Получает все живые фьючерсные пары, проходящие фильтр по суточному объему"""
    url = f"{BINGX_URL}/openApi/swap/v2/quote/ticker"
    try:
        response = requests.get(url).json()
        if response.get("code") == 0:
            valid_symbols = []
            for item in response["data"]:
                symbol = item["symbol"]
                # Фильтруем только USDT пары
                if symbol.endswith("-USDT"):
                    vol_24h = float(item.get("volume", 0)) * float(item.get("lastPrice", 0))
                    # Отсекаем мертвые пары с накрученными копеечными объемами
                    if vol_24h >= MIN_VOLUME_24H:
                        valid_symbols.append({
                            "symbol": symbol,
                            "price": float(item["lastPrice"]),
                            "vol24h": vol_24h
                        })
            return valid_symbols
    except Exception as e:
        print(f"Ошибка получения списка фьючерсов: {e}")
    return []

def check_recent_liquidations(symbol, current_price, vol24h):
    """Проверяет минутные свечи ликвидаций на BingX"""
    # Используем официальный эндпоинт истории свечей ликвидаций
    url = f"{BINGX_URL}/openApi/swap/v2/quote/liquidation"
    params = {
        "symbol": symbol,
        "limit": 2 # Смотрим самую свежую закрытую минуту
    }
    
    try:
        response = requests.get(url, params=params).json()
        if response.get("code") != 0 or not response.get("data"):
            return
        
        # Получаем данные последней активности
        data = response["data"]
        for record in data:
            # Считаем объем ликвидации в USDT
            liq_qty = float(record.get("volume", 0))
            liq_price = float(record.get("price", current_price))
            liq_usd = liq_qty * liq_price
            
            # Если ликвидация крупная — генерируем сигнал
            if liq_usd >= MIN_LIQ_AMOUNT:
                side = record.get("side") # BUY (Ликвидация Шорта) или SELL (Ликвидация Лонга)
                send_alert(symbol, side, liq_usd, liq_price, vol24h)
                break # Отправили один алерт и выходим, чтобы не спамить
    except:
        pass

def send_alert(symbol, side, amount_usd, price, vol24h):
    """Форматирует и отправляет сообщение в Телеграм"""
    
    # Стилизуем под тип сквиза
    if side == "SELL" or side == "Sell":
        emoji = "🩸 **ЛОНГ-СКВИЗ (ПАДЕНИЕ)** 🩸"
        action = "Разгрузили покупателей. Ищем точку на V-образный ОТСКОК ВВЕРХ! 🟢"
    else:
        emoji = "🔥 **ШОРТ-СКВИЗ (ПАМП)** 🔥"
        action = "Выбили продавцов. Потенциальный разворот или откат ВНИЗ! 🔴"
        
    message = (
        f"{emoji}\n\n"
        f"🔹 **Монета:** #{symbol.replace('-', '_')}\n"
        f"💵 **Цена ликвидации:** {price}\n"
        f"💰 **Сумма ликвидации:** ${amount_usd:,.2f}\n\n"
        f"📊 **Ликвидность рынка:**\n"
        f"└ Суточный объем пары: ${vol24h/1_000_000:.1f}M\n\n"
        f"⚡ **Действие:** {action}\n\n"
        f"🔗 [График TradingView](https://ru.tradingview.com/chart/?symbol=BINGX:{symbol.replace('-', '')})"
    )
    
    try:
        bot.send_message(CHAT_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
        print(f"🔥 Сигнал ликвидации по {symbol} на ${amount_usd:.0f} отправлен!")
    except Exception as e:
        print(f"Ошибка отправки в ТГ: {e}")

def run_screener():
    """Поминутный цикл проверки"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Сканирование ликвидаций...")
    active_coins = get_active_futures()
    
    for coin in active_coins:
        # Небольшая пауза между запросами, чтобы биржа не забанила по лимитам
        time.sleep(0.1)
        check_recent_liquidations(coin["symbol"], coin["price"], coin["vol24h"])

if __name__ == "__main__":
    # Скринер теперь работает постоянно, запускаясь каждую минуту
    while True:
        try:
            run_screener()
        except Exception as e:
            print(f"Критическая ошибка цикла: {e}")
        # Спим 60 секунд до следующего раунда проверок
        time.sleep(60)
