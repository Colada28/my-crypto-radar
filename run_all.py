import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- 1. МИКРО-ВЕБ-СЕРВЕР ДЛЯ ОБМАНА RENDER ---
class SimpleWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Crypto Radar is successfully running!".encode("utf-8"))

    def log_message(self, format, *args):
        return

def run_web_server():
    server_address = ("", 10000)
    httpd = HTTPServer(server_address, SimpleWebHandler)
    print("🌍 Микро-веб-сервер запущен для Render на порту 10000", flush=True)
    httpd.serve_forever()

# --- 2. ЗАПУСК НАШИХ СКРИНЕРОВ ---
def run_screener(script_name):
    while True:
        try:
            print(f"🚀 Запуск скринера: {script_name}...", flush=True)
            # Флаг -u отключает буферизацию, логи будут видны сразу!
            process = subprocess.Popen([sys.executable, "-u", script_name])
            process.wait()
        except Exception as e:
            print(f"❌ Ошибка в работе {script_name}: {e}", flush=True)
        print(f"⏳ Перезапуск {script_name} через 5 секунд...", flush=True)
        time.sleep(5)

if __name__ == "__main__":
    print("--- Запуск глобальной экосистемы скринеров ---", flush=True)

    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    time.sleep(2)

    # Запускаем параллельно оба скринера
    bybit_thread = threading.Thread(target=run_screener, args=("pump_screener.py",), daemon=True)
    bingx_thread = threading.Thread(target=run_screener, args=("short_screener.py",), daemon=True)

    bybit_thread.start()
    bingx_thread.start()

    # Удерживаем главный поток живым
    while True:
        time.sleep(3600)
