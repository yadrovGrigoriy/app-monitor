"""Fix double backslashes in installer.nsi paths."""
with open('installer/installer.nsi', 'r', encoding='cp1251') as f:
    data = f.read()

data = data.replace('v1.2.36\\\\', 'v1.2.36\\')

with open('installer/installer.nsi', 'w', encoding='cp1251') as f:
    f.write(data)

print('OK: installer.nsi paths fixed')
