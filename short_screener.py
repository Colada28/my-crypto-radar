import time
import requests
import telebot

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8834450636:AAH0vH2ayzopTG2atZEezEa5PWkvKMV_Sxs"
CHAT_ID = "-1003714825454"

BINGX_URL = "https://open-api.bingx.com"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def get_all_futures_symbols():
    """Получает список всех доступных фьючерсных пар на BingX"""
    url = f"{BINGX_URL}/openApi/swap/v2/quote/ticker"
    try:
        response = requests.get(url).json()
        if response.get("code") == 0:
            return [item for item in response["data"] if item["symbol"].endswith("-USDT")]
    except Exception as e:
        print(f"Ошибка получения тикеров: {e}")
    return []

def get_funding_rate(symbol):
    """Получает текущую ставку финансирования для конкретной монеты"""
    url = f"{BINGX_URL}/openApi/swap/v2/quote/fundingRate"
    params = {"symbol": symbol}
    try:
        response = requests.get(url, params=params).json()
        if response.get("code") == 0:
            return float(response["data"].get("fundingRate", 0))
    except:
        pass
    return 0.0

def analyze_coin(symbol, current_price):
    """Анализирует историю дневных свечей монеты за последние 60 дней"""
    url = f"{BINGX_URL}/openApi/swap/v3/quote/klines"
    params = {
        "symbol": symbol,
        "interval": "1d",
        "limit": 60
    }
    
    try:
        response = requests.get(url, params=params).json()
        if response.get("code") != 0 or not response.get("data"):
            return None
        
        klines = response["data"]
        if len(klines) < 30:
            return None
            
        high_prices = [float(candle[2]) for candle in klines]
        low_prices = [float(candle[3]) for candle in klines]
        volumes = [float(candle[5]) for candle in klines]
        
        ath_60d = max(high_prices)
        atl_60d = min(low_prices)
        
        pump_percentage = ((ath_60d - atl_60d) / atl_60d) * 100
        if pump_percentage < 300:
            return None
            
        distance_from_ath = ((ath_60d - current_price) / ath_60d) * 100
        if not (1.0 <= distance_from_ath <= 10.0):
            return None
            
        peak_volume = max(volumes)
        recent_avg_volume = sum(volumes[-3:]) / 3
        
        if recent_avg_volume > (peak_volume * 0.7):
            return None
            
        return {
            "pump": pump_percentage,
            "ath_dist": distance_from_ath,
            "peak_vol": peak_volume,
            "recent_vol": recent_avg_volume
        }
    except Exception as e:
        print(f"Ошибка анализа истории для {symbol}: {e}")
    return None

def scan_market():
    """Основной цикл сканирования рынка"""
    print("Запуск глобального сканирования рынка BingX...")
    tickers = get_all_futures_symbols()
    
    for ticker in tickers:
        symbol = ticker["symbol"]
        current_price = float(ticker["lastPrice"])
        
        time.sleep(0.2)
        
        analysis = analyze_coin(symbol, current_price)
        if analysis:
            funding = get_funding_rate(symbol)
            funding_pct = funding * 100
            
            if funding_pct > 0.02:
                funding_status = f"{funding_pct:.4f}% 🟢 (Лонги платят шортам)"
            elif funding_pct < 0.0:
                funding_status = f"{funding_pct:.4f}% 🔴 (Шорты платят лонгам! Опасно)"
            else:
                funding_status = f"{funding_pct:.4f}% 🟡 (Нейтральный)"
                
            message = (
                f"🚨 **ГЛОБАЛЬНЫЙ ШОРТ-СИГНАЛ** 🚨\n\n"
                f"🔹 **Монета:** #{symbol.replace('-', '_')}\n"
                f"💵 **Текущая цена:** {current_price}\n\n"
                f"📊 **Метрики за 60 дней:**\n"
                f"├ Истинный памп от дна: +{analysis['pump']:.1f}%\n"
                f"└ Дистанция под ATH: -{analysis['ath_dist']:.1f}% (Полка)\n\n"
                f"📉 **Затухание объемов:**\n"
                f"├ Пиковый суточный объем: {analysis['peak_vol']:.1f}\n"
                f"└ Средний объем за 3 дня: {analysis['recent_vol']:.1f}\n\n"
                f"💸 **Ставка финансирования:**\n"
                f"└ {funding_status}\n\n"
                f"🔗 [Открыть график на TradingView](https://ru.tradingview.com/chart/?symbol=BINGX:{symbol.replace('-', '')})"
            )
            
            try:
                bot.send_message(CHAT_ID, message, parse_mode="Markdown", disable_web_page_preview=True)
                print(f"Сигнал по {symbol} успешно отправлен!")
            except Exception as e:
                print(f"Не удалось отправить сообщение в ТГ: {e}")

if __name__ == "__main__":
    while True:
        try:
            scan_market()
        except Exception as e:
            print(f"Ошибка в цикле сканирования: {e}")
            
        print("Сканирование завершено. Засыпаю на 4 часа...")
        time.sleep(14400)  # Пауза 4 часа между проверками рынка
