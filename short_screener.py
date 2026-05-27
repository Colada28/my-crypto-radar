import time
from datetime import datetime
import requests
import telebot

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8834450636:AAH0vH2ayzopTG2atZEezEa5PWkvKMV_Sxs"
CHAT_ID = "-1003714825454"

BYBIT_URL = "https://api.bybit.com"

# НАСТРОЙКИ ФИЛЬТРОВ ЛИКВИДАЦИЙ
MIN_VOLUME_24H = 1000000  # От $1,000,000 объема за сутки
MIN_LIQ_AMOUNT = 3000     # Триггер: ликвидация от $3,000 за один ордер

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def get_active_futures():
    """Получает active пары с Bybit для фильтрации по объему"""
    url = f"{BYBIT_URL}/v5/market/tickers?category=linear"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            response = res.json()
            if response.get("retCode") == 0:
                valid_symbols = {}
                for item in response["result"]["list"]:
                    symbol = item["symbol"]
                    if symbol.endswith("USDT"):
                        vol_24h = float(item.get("turnover24h", 0))
                        if vol_24h >= MIN_VOLUME_24H:
                            valid_symbols[symbol] = {
                                "price": float(item.get("lastPrice", 0)),
                                "vol24h": vol_24h
                            }
                return valid_symbols
    except Exception as e:
        print(f"Ошибка получения объемов Bybit: {e}")
    return {}

def check_bybit_liquidations(active_coins):
    """Проверяет последние крупные сделки на Bybit"""
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
            if symbol not in active_coins:
                continue
                
            price = float(trade.get("price", 0))
            qty = float(trade.get("size", 0))
            amount_usd = qty * price
            
            if amount_usd >= MIN_LIQ_AMOUNT:
                side = trade.get("side")
                vol24h = active_coins[symbol]["vol24h"]
                
                send_alert(symbol, side, amount_usd, price, vol24h)
                time.sleep(1)
                
    except Exception as e:
        print(f"Ошибка парсинга ленты Bybit: {e}")

def send_alert(symbol, side, amount_usd, price, vol24h):
    """Форматирует и отправляет сообщение в Телеграм"""
    if side in ["Sell", "SELL"]:
        emoji = "🩸 **КРУПНЫЙ СБРОС / ЛОНГ-ЛИКВИДАЦИЯ** 🩸"
        action = "Маркет-мейкер смыл покупателей. Отскок или В-образный разворот вверх! 🟢"
    else:
        emoji = "🔥 **ИМПУЛЬСНЫЙ ПРОБИЙ / ШОРТ-ЛИКВИДАЦИЯ** 🔥"
        action = "Продавцов вынесло по стопам. Потенциальный разворот рынка вниз! 🔴"
        
    message = (
        f"{emoji}\n\n"
        f"🔹 **Монета:** #{symbol}\n"
        f"💵 **Цена исполнения:** {price}\n"
        f"💰 **Объем сквиза:** ${amount_usd:,.2f}\n\n"
        f"📊 **Ликвидность площадки:**\n"
        f"└ Суточный объем Bybit: ${vol24h/1_000_000:.1f}M\n\n"
        f"⚡ **Действие:** {action}\n\n"
        f"🔗 [График TradingView](https://ru.tradingview.com/chart/?symbol=BYBIT:{symbol})"
    )
    
    try:
        bot.send_message(CHAT_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
        print(f"🔥 Сигнал крупного сквиза по {symbol} на ${amount_usd:.0f} отправлен!")
    except Exception as e:
        print(f"Ошибка отправки в ТГ: {e}")

if __name__ == "__main__":
    print("=== Скринер крупных ордеров и сквизов Bybit успешно запущен ===")
    
    try:
        bot.send_message(CHAT_ID, "🚀 Бот-радар Крупных Сквизов (Bybit) успешно запущен на Render!")
    except Exception as e:
        print(f"Ошибка отправки стартового ТГ: {e}")

    while True:
        try:
            active_coins = get_active_futures()
            if active_coins:
                check_bybit_liquidations(active_coins)
        except Exception as e:
            print(f"Критическая ошибка цикла: {e}")
        time.sleep(10)
