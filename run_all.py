import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- 1. МИКРО-ВЕБ-СЕРВЕР ДЛЯ ОБМАНА RENDER ---
class SimpleWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Crypto Radar is successfully running!")

    def log_message(self, format, *args):
        # Отключаем лишний спам в логи Render
        return

def run_web_server():
    # Render по умолчанию дает порт 10000, если его нет — берем стандартный
    server_address = ("", 10000)
    httpd = HTTPServer(server_address, SimpleWebHandler)
    print("🌍 Микро-веб-сервер запущен для Render на порту 10000")
    httpd.serve_forever()

# --- 2. ЗАПУСК НАШИХ СКРИНЕРОВ ---
def run_screener(script_name):
    """Функция для непрерывного запуска скрипта"""
    while True:
        try:
            print(f"🚀 Запуск скринера: {script_name}...")
            # Запускаем скрипт и ждем его логи в реальном времени
            process = subprocess.Popen([sys.executable, script_name])
            process.wait()
        except Exception as e:
            print(f"❌ Ошибка в работе {script_name}: {e}")
        print(f"⏳ Перезапуск {script_name} через 5 секунд...")
        time.sleep(5)

if __name__ == "__main__":
    print("=== Запуск глобальной экосистемы скринеров ===")

    # 1. Запускаем веб-сервер в отдельном потоке, чтобы Render не ругался на порты
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Маленькая пауза перед запуском тяжелых скриптов
    time.sleep(2)

    # 2. Запускаем параллельно оба скринера в отдельных потоках
    bybit_thread = threading.Thread(target=run_screener, args=("pump_screener.py",), daemon=True)
    bingx_thread = threading.Thread(target=run_screener, args=("short_screener.py",), daemon=True)

    bybit_thread.start()
    bingx_thread.start()

    # Держим главный процесс запущенным
    while True:
        time.sleep(3600)
