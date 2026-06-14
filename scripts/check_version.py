"""Проверить версию в исходниках и в собранном exe."""
import re
import struct
import tomllib

# 1. Проверяем pyproject.toml
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
src_version = data['project']['version']
print(f'pyproject.toml version: {src_version}')

# 2. Проверяем updater.py
with open('core/updater.py', 'r', encoding='utf-8') as f:
    content = f.read()
m = re.search(r'APP_VERSION\s*=\s*"([\d.]+)"', content)
if m:
    updater_version = m.group(1)
    print(f'updater.py APP_VERSION: {updater_version}')
else:
    updater_version = None
    print('APP_VERSION not found in updater.py')

# 3. Проверяем собранный exe
with open('dist/AppMonitor.exe', 'rb') as f:
    exe_data = f.read()

# PE header
pe_offset = struct.unpack('<I', exe_data[0x3C:0x40])[0]
opt_header = pe_offset + 4 + 20
subsystem = struct.unpack('<H', exe_data[opt_header + 68:opt_header + 70])[0]
print(f'Exe subsystem: {subsystem} (2=GUI)')

# Ищем версию в байткоде (PyInstaller хранит .pyc)
# Ищем строку вида 1.2.XX
matches = re.findall(rb'1\.2\.\d{2}', exe_data)
print(f'Найдено строк 1.2.XX в exe: {len(matches)}')
for m in matches[:10]:
    print(f'  {m.decode()}')

# Ищем просто 1.2.
matches2 = re.findall(rb'1\.2\.', exe_data)
print(f'Найдено строк 1.2. в exe: {len(matches2)}')
