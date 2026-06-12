path = 'installer/installer.nsi'
with open(path, 'rb') as f:
    d = f.read()
print('Size:', len(d))
idx = d.find(b'OutFile')
print('OutFile:', d[idx:idx+70])
idx2 = d.find(b'File "..')
print('File:', d[idx2:idx2+50])
