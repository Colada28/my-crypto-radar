import requests
import time

# Твой новый рабочий токен и канал
TOKEN = "8941415221:AAHX-1F901LYEatcMEBqJFdTE7QpGbp4t88"
CHAT_ID = "@alexey_pump_alerts_new"

LONG_TRIGGER = 0.001       
SHORT_TRIGGER = -0.001   
MIN_VOLUME_M = 0.1       

LAST_SIGNAL_TIMES = {}
SIGNAL_COOLDOWN = 300    

def send_telegram_message(text):
    if not TOKEN:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("[ТГ ЛОГ] Сообщение успешно отправлено!")
        else:
            print(f"[ТГ ОШИБКА]: Код {response.status_code}, Ответ: {response.text}")
    except Exception as e:
        print(f"[ТГ СИСТЕМНАЯ ОШИБКА]: {e}")

def get_bybit_tickers():
    url = "https://api.bybit.com/v5/market/tickers?category=linear"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("retCode") == 0:
                return data["result"]["list"]
    except Exception as e:
        print(f"[BYBIT ОШИБКА]: {e}")
    return []

def main():
    print("🚀 [СИСТЕМА] Фоновый движок сканера Bybit запущен успешно!")
    time.sleep(5)
    
    send_telegram_message("🤖 *Бот-радар успешно запущен на Render по старому коду!*")
    
    prices_history = {}
    
    while True:
        tickers = get_bybit_tickers()
        current_time = time.time()
        
        if tickers:
            for ticker in tickers:
                symbol = ticker["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                    
                current_price = float(ticker["lastPrice"])
                volume_24h = float(ticker["turnover24h"]) / 1_000_000 
                
                if symbol not in prices_history:
                    prices_history[symbol] = []
                
                prices_history[symbol].append((current_time, current_price))
                prices_history[symbol] = [p for p in prices_history[symbol] if current_time - p[0] <= 300]
                
                old_price = prices_history[symbol][0][1]
                if old_price == 0:
                    continue
                    
                price_change = ((current_price - old_price) / old_price) * 100
                
                if volume_24h >= MIN_VOLUME_M:
                    is_long = price_change >= LONG_TRIGGER
                    is_short = price_change <= SHORT_TRIGGER
                    
                    if is_long or is_short:
                        if symbol in LAST_SIGNAL_TIMES:
                            if current_time - LAST_SIGNAL_TIMES[symbol] < SIGNAL_COOLDOWN:
                                continue
                        
                        clean_symbol = symbol.replace("USDT", "")
                        coinglass_url = f"https://www.coinglass.com/pro/futures/LiquidationChart/BingX/{clean_symbol}"
                        
                        if is_long:
                            msg = (
                                f"🟢 *ИМПУЛЬС ВВЕРХ* 📈\n\n"
                                f"🔹 *Монета:* #{clean_symbol} (BingX)\n"
                                f"📊 *Изменение за 5м:* +{price_change:.2f}%\n"
                                f"💰 *Цена:* {current_price}\n"
                                f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                                f"🔗 [Открыть график на Coinglass]({coinglass_url})"
                            )
                        else:
                            msg = (
                                f"🔴 *ИМПУЛЬС ВНИЗ* 📉\n\n"
                                f"🔹 *Монета:* #{clean_symbol} (BingX)\n"
                                f"📊 *Изменение за 5м:* {price_change:.2f}%\n"
                                f"💰 *Цена:* {current_price}\n"
                                f"💵 *Объем 24h:* {volume_24h:.2f}M USDT\n\n"
                                f"🔗 [Открыть график на Coinglass]({coinglass_url})"
                            )
                        
                        LAST_SIGNAL_TIMES[symbol] = current_time
                        send_telegram_message(msg)
                        print(f"[СИГНАЛ] Отправлено оповещение по {clean_symbol}")
                        
        time.sleep(15)

if __name__ == "__main__":
    main()
