import threading
import time
import os
import sys

def run_pump_screener():
    print("🚀 Запуск скринера: pump_screener.py...", flush=True)
    try:
        import pump_screener
    except Exception as e:
        print(f"❌ Ошибка в pump_screener: {e}", flush=True)

def run_short_screener():
    print("🚀 Запуск скринера: short_screener.py...", flush=True)
    try:
        import short_screener
    except Exception as e:
        print(f"❌ Ошибка в short_screener: {e}", flush=True)

if __name__ == "__main__":
    print("--- Запуск глобальной экосистемы скринеров без JSON-ошибок ---", flush=True)
    
    # Запускаем каждый скринер в отдельном потоке, полностью изолируя их
    t1 = threading.Thread(target=run_pump_screener, daemon=True)
    t2 = threading.Thread(target=run_short_screener, daemon=True)
    
    t1.start()
    time.sleep(2) # Небольшая пауза, чтобы первый бот успел занять порт 10000
    t2.start()
    
    # Держим главный процесс активным
    while True:
        time.sleep(10)
