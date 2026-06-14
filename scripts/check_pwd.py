import hashlib
h = '1d5411a1740daae1ad5e803e6fcfd0cd:5e10cb6a1ab1b8e9a7c210df1e4657442efa5585358745ef775f7fd728217d9d'
s, e = h.split(':', 1)
for p in ['admin', 'M@yonez_souse', 'password', 'admin123']:
    r = hashlib.sha256(f'{s}:{p}'.encode()).hexdigest()
    print(f'{"✓" if r == e else "✗"} {p}')
