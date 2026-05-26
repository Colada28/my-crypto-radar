import subprocess
import sys
import time

print("Запуск единого диспетчера ботов...")

# Запускаем первого бота (Bybit) в фоновом процессе
process_bybit = subprocess.Popen([sys.executable, "-u", "pump_screener.py"])
print("Старый памп-скринер Bybit запущен.")

# Запускаем второго бота (BingX) во втором фоновом процессе
process_bingx = subprocess.Popen([sys.executable, "-u", "short_screener.py"])
print("Новый шорт-скринер BingX запущен.")

# Бесконечный цикл для контроля работы
try:
    while True:
        # Если первый бот упадет, диспетчер его поднимет
        if process_bybit.poll() is not None:
            print("Внимание: Скринер Bybit остановился. Перезапуск...")
            process_bybit = subprocess.Popen([sys.executable, "-u", "pump_screener.py"])
            
        # Если второй бот упадет, диспетчер его поднимет
        if process_bingx.poll() is not None:
            print("Внимание: Скринер BingX остановился. Перезапуск...")
            process_bingx = subprocess.Popen([sys.executable, "-u", "short_screener.py"])
            
        time.sleep(60) # Проверка статуса процессов каждую минуту
except KeyboardInterrupt:
    print("Остановка диспетчера...")
    process_bybit.terminate()
    process_bingx.terminate()
