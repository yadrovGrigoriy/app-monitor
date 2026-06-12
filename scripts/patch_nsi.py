"""Патч installer.nsi: обновить версию и пути."""
import re
import sys

path = sys.argv[1]
new_version = sys.argv[2]
version_folder = sys.argv[3].replace('/', '\\')  # например dist\v1.2.21

with open(path, 'rb') as f:
    data = f.read()

# Обновляем версию
data = re.sub(
    rb'!define PRODUCT_VERSION "[\d.]+"',
    f'!define PRODUCT_VERSION "{new_version}"'.encode('cp1251'),
    data
)

# Обновляем OutFile
data = data.replace(
    b'..\\dist\\AppMonitor_Setup_',
    f'..\\{version_folder}\\AppMonitor_Setup_'.encode('cp1251')
)

# Обновляем File
data = data.replace(
    b'..\\dist\\AppMonitor.exe',
    f'..\\{version_folder}\\AppMonitor.exe'.encode('cp1251')
)

with open(path, 'wb') as f:
    f.write(data)

print(f'OK: {path} patched to v{new_version} in {version_folder}')
