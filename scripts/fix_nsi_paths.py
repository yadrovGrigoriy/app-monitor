"""Fix double backslashes in installer.nsi paths."""
path = 'installer/installer.nsi'
with open(path, 'r', encoding='cp1251') as f:
    data = f.read()

data = data.replace('v1.2.36\\\\', 'v1.2.36\\')

with open(path, 'w', encoding='cp1251') as f:
    f.write(data)

print('OK: installer.nsi paths fixed')
