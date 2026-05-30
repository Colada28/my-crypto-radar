import time
import threading
from flask import Flask

TOKEN = "8941415221:AAHX-1F901LYEatcMEBqJFdTE7QpGbp4t88"
CHAT_ID = "-1003959408476"

def radar_loop():
    print("Radar loop started")
    while True:
        time.sleep(5)

app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

if __name__ == "__main__":
    time.sleep(2)
    t = threading.Thread(target=radar_loop)
    t.daemon = True
    t.start()

    app.run(host="0.0.0.0", port=10000)
