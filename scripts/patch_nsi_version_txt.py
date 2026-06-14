"""Добавить File version.txt в installer.nsi после File AppMonitor.exe."""
import sys

path = sys.argv[1]

with open(path, 'rb') as f:
    data = f.read()

old = b'    File "..\\dist\\v1.2.35\\AppMonitor.exe"\r\n'
new = b'    File "..\\dist\\v1.2.35\\AppMonitor.exe"\r\n    File "..\\version.txt"\r\n'

if old not in data:
    print('ERROR: old text not found')
    # Ищем любой File
    idx = data.find(b'File "..\\')
    if idx >= 0:
        print(f'First File at: {idx}')
        print(repr(data[idx:idx+80]))
    sys.exit(1)

data = data.replace(old, new)
with open(path, 'wb') as f:
    f.write(data)
print('OK')
