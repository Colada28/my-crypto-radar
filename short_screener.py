import time
from datetime import datetime
import requests
import telebot

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8834450636:AAH0vH2ayzopTG2atZEezEa5PWkvKMV_Sxs"
CHAT_ID = "-1003714825454"

BINGX_URL = "https://open-api.bingx.com"

# МИНИМАЛЬНЫЙ ПОРОГ ЛИКВИДНОСТИ
MIN_VOLUME_24H = 1000000  # От $1,000,000 объема за сутки
MIN_LIQ_AMOUNT = 3000    # Ликвидация от $3,000 за одну свечу

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def get_active_futures():
    """Получает все живые фьючерсные пары, проходящие фильтр по суточному объему"""
    url = f"{BINGX_URL}/openApi/swap/v2/quote/ticker"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            print(f"⏳ BingX API недоступен при получении тикеров (Статус: {res.status_code})")
            return []
            
        response = res.json()
        if response.get("code") == 0:
            valid_symbols = []
            for item in response["data"]:
                symbol = item["symbol"]
                if symbol.endswith("-USDT"):
                    vol_24h = float(item.get("volume", 0)) * float(item.get("lastPrice", 0))
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
    """Проверяет минутные свечи ликвидаций на BingX с защитой от ошибок парсинга"""
    url = f"{BINGX_URL}/openApi/swap/v2/quote/liquidation"
    params = {"symbol": symbol, "limit": 2}
    
    try:
        res = requests.get(url, params=params, timeout=10)
        
        # Если поймали ограничение частоты запросов (Rate Limit / Cloudflare)
        if res.status_code == 429 or res.status_code == 403:
            print("🛑 Превышен лимит запросов к BingX. Включаем режим ожидания...")
            time.sleep(30)
            return
            
        if res.status_code != 200:
            return

        response = res.json()
        if response.get("code") != 0 or not response.get("data"):
            return
        
        data = response["data"]
        for record in data:
            liq_qty = float(record.get("volume", 0))
            liq_price = float(record.get("price", current_price))
            liq_usd = liq_qty * liq_price
            
            if liq_usd >= MIN_LIQ_AMOUNT:
                side = record.get("side")
                send_alert(symbol, side, liq_usd, liq_price, vol24h)
                break
    except Exception:
        # Беззвучно пропускаем ошибки парсинга HTML-страниц блокировок
        pass

def send_alert(symbol, side, amount_usd, price, vol24h):
    """Форматирует и отправляет сообщение в Телеграм"""
    if side in ["SELL", "Sell"]:
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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Сканирование ликвидаций BingX...")
    active_coins = get_active_futures()
    
    if not active_coins:
        return

    for coin in active_coins:
        # Пауза 0.25 сек, чтобы не злить Cloudflare биржи BingX
        time.sleep(0.25)
        check_recent_liquidations(coin["symbol"], coin["price"], coin["vol24h"])

if __name__ == "__main__":
    print("=== Скринер ликвидаций BingX успешно инициализирован ===")
    
    # Отправляем тестовое уведомление в Телеграм при старте:
    try:
        bot.send_message(CHAT_ID, "🚀 Бот-радар BingX (Ликвидации) успешно запущен на бесплатном Web Service!")
    except Exception as e:
        print(f"Ошибка отправки стартового ТГ: {e}")

    while True:
        try:
            run_screener()
        except Exception as e:
            print(f"Критическая ошибка цикла BingX: {e}")
        time.sleep(60)
