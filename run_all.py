import os
import sys
import subprocess

print("=== Запуск последовательного сканирования рынков ===")

# 1. Запуск скринера Bybit (он отработает быстро и закроется)
print("Запуск сканирования Bybit...")
subprocess.run([sys.executable, "-u", "pump_screener.py"])

# 2. Запуск скринера BingX (он проверит время: либо пропустит, либо просканирует)
print("Запуск сканирования BingX...")
subprocess.run([sys.executable, "-u", "short_screener.py"])

print("=== Все проверки завершены. Контейнер свободен ===")
