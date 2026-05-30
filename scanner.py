import requests
import time
from flask import Flask

TOKEN = "ВСТАВЬ_СВОЙ_ТОКЕН"
CHAT_ID = "ВСТАВЬ_СВОЙ_CHAT_ID"

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

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

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

if __name__ == "__main__":
    import threading
    t = threading.Thread(target=scanner_loop)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=10000)
