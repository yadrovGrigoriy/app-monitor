"""Найти и показать лог установщика AppMonitor."""
import os
import glob

paths = [
    r'C:\ProgramData\AppMonitor\logs\install_*.log',
    r'C:\ProgramData\AppMonitor\install_*.log',
]

for pattern in paths:
    files = glob.glob(pattern)
    if files:
        latest = max(files, key=os.path.getmtime)
        print('Найден лог: ' + latest)
        print('Размер: ' + str(os.path.getsize(latest)) + ' bytes')
        print()
        with open(latest, 'r', encoding='utf-8') as f:
            print(f.read())
        break
else:
    print('Логов установщика не найдено.')
    for d in [r'C:\ProgramData\AppMonitor', r'C:\ProgramData\AppMonitor\logs']:
        if os.path.isdir(d):
            print('Папка существует: ' + d)
            print('Содержимое: ' + str(os.listdir(d)))
        else:
            print('Папка НЕ существует: ' + d)
