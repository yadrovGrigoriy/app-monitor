"""
Скачивание NSIS установщика.
"""
import urllib.request
import os
import sys

url = 'https://sourceforge.net/projects/nsis/files/NSIS%203/3.12/nsis-3.12-setup.exe/download'
dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nsis-setup.exe')

print(f'Скачивание NSIS...')
urllib.request.urlretrieve(url, dest)
size_mb = os.path.getsize(dest) / (1024 * 1024)
print(f'Скачано: {dest} ({size_mb:.1f} MB)')
