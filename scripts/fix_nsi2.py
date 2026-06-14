"""Исправить двойные/тройные слеши в installer.nsi."""
path = 'installer/installer.nsi'
with open(path, 'rb') as f:
    data = f.read()

# Заменяем ..\dist\vX.Y.Z\\... на ..\dist\vX.Y.Z\...
# В байтах: 2E 2E 5C 64 69 73 74 5C 76 ... 5C 5C -> 5C
import re
# OutFile: ищем ..\dist\v...\\(один или больше)AppMonitor_Setup_
data = re.sub(
    rb'(OutFile "\.\.[\\/]dist[\\/]v[\d.]+[\\/])\\+',
    rb'\1',
    data
)
# File: ищем ..\dist\v...\\(один или больше)AppMonitor.exe
data = re.sub(
    rb'(File "[^"]*\.\.[\\/]dist[\\/]v[\d.]+[\\/])\\+',
    rb'\1',
    data
)

with open(path, 'wb') as f:
    f.write(data)

# Проверка
for m in re.finditer(rb'OutFile "[^"]+"', data):
    print('OUT:', m.group())
for m in re.finditer(rb'File "[^"]+AppMonitor\.exe"', data):
    print('FILE:', m.group())
print('OK')
