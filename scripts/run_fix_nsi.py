"""Check password and fix installer paths."""
import hashlib
import os
import subprocess
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── Check default admin password ───
stored_hash = '1d5411a1740daae1ad5e803e6fcfd0cd:5e10cb6a1ab1b8e9a7c210df1e4657442efa5585358745ef775f7fd728217d9d'
salt, expected = stored_hash.split(':', 1)

candidates = ['admin', 'M@yonez_souse', 'password', 'admin123', '123456', 'pass', 'qwerty']
for pwd in candidates:
    h = hashlib.sha256(f'{salt}:{pwd}'.encode()).hexdigest()
    match = '✓' if h == expected else '✗'
    print(f'{match} {pwd}')

# ─── Fix installer.nsi paths ───
path = 'installer/installer.nsi'
with open(path, 'r', encoding='cp1251') as f:
    data = f.read()

data = data.replace('v1.2.36\\\\', 'v1.2.36\\')

with open(path, 'w', encoding='cp1251') as f:
    f.write(data)

print('OK: installer.nsi paths fixed')
