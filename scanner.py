import requests
import time
from flask import Flask

# -----------------------------
#  ТВОИ ДАННЫЕ ДЛЯ TELEGRAM
# -----------------------------
TOKEN = "8941415221:AAHX-1F901LYEatcMEBqJFdTE7QpGbp4t88"
CHAT_ID = "-1003959408476"

# -----------------------------
#  ФУНКЦИЯ ОТПРАВКИ СООБЩЕНИЙ
# -----------------------------
def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

# -----------------------------
#  ПРОСТОЙ BTC SCANNER
# -----------------------------
def get_price():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        return float(r.json()["price"])
    except:
        return None

def scanner_loop():
    last_price = None

    while True:
        price = get_price()
        if price:
            if last_price and abs(price - last_price) > 100:
                send(f"⚡ BTC движение: {price} USDT")
            last_price = price

        time.sleep(10)

# -----------------------------
#  FLASK ДЛЯ RENDER (НЕ ЗАСЫПАЕТ)
# -----------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

# -----------------------------
#  ЗАПУСК
# -----------------------------
if __name__ == "__main__":
    import threading

    # Запускаем сканер в отдельном потоке
    t = threading.Thread(target=scanner_loop)
    t.daemon = True
    t.start()

    # Запускаем Flask-сервер
    app.run(host="0.0.0.0", port=10000)
