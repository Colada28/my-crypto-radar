import subprocess
import sys
import time

def start_screener(script_name):
    """Запускает скрипт как независимый процесс ОС"""
    print(f"🚀 Принудительный изолированный запуск: {script_name}...", flush=True)
    return subprocess.Popen([sys.executable, script_name])

if __name__ == "__main__":
    print("--- Полная изоляция процессов запущена ---", flush=True)
    
    # Запускаем скрипты как два абсолютно независимых процесса
    process_pump = start_screener("pump_screener.py")
    
    # Небольшая пауза в 5 секунд, чтобы первый скрипт успел занять порт 10000
    time.sleep(5) 
    
    process_short = start_screener("short_screener.py")
    
    # Контролируем, чтобы процессы не умерли
    while True:
        # Если какой-то из процессов упадет, мы увидим это в логах
        if process_pump.poll() is not None:
            print("⚠️ Внимание: pump_screener.py завершил работу.", flush=True)
        if process_short.poll() is not None:
            print("⚠️ Внимание: short_screener.py завершил работу.", flush=True)
            
        time.sleep(15)
