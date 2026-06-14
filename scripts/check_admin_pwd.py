"""Check what password corresponds to the hardcoded hash."""
import hashlib
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

stored_hash = '1d5411a1740daae1ad5e803e6fcfd0cd:5e10cb6a1ab1b8e9a7c210df1e4657442efa5585358745ef775f7fd728217d9d'
salt, expected = stored_hash.split(':', 1)

candidates = ['admin', 'Admin', 'password', 'admin123', 'M@yonez_souse', '123456', 'admin1', 'pass', 'admin1234', 'qwerty']

for pwd in candidates:
    h = hashlib.sha256(f'{salt}:{pwd}'.encode()).hexdigest()
    match = '✓' if h == expected else '✗'
    print(f'{match} {pwd}')

print()
print(f'Salt: {salt}')
print(f'Expected: {expected}')
