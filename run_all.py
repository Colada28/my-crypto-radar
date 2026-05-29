import os
import http.server
import threading
import subprocess

def start_simple_http_server():
    port = int(os.environ.get('PORT', 10000))
    server_address = ('', port)
    class SimpleHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
    httpd = http.server.HTTPServer(server_address, SimpleHandler)
    print(f"Web server started on port {port}", flush=True)
    httpd.serve_forever()

if __name__ == "__main__":
    # Запуск веб-сервера в отдельном потоке для заглушки Render
    threading.Thread(target=start_simple_http_server, daemon=True).start()
    
    # Запуск твоего главного работающего скрипта
    print("Starting pump_screener.py...", flush=True)
    subprocess.run(["python", "pump_screener.py"])
