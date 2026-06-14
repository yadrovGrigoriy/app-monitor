"""Patch installer.nsi: update -PostInstall section for auto-update."""
import sys

path = sys.argv[1]

with open(path, 'rb') as f:
    data = f.read()

old = (
    b'Section -PostInstall\r\n'
    b'    Sleep 1000\r\n'
    b'    Exec "$INSTDIR\\AppMonitor.exe"\r\n'
    b'SectionEnd'
)

new = (
    b'Section -PostInstall\r\n'
    b'    ${If} $AUTORUN_FLAG == "1"\r\n'
    b'        Sleep 2000\r\n'
    b'        nsExec::ExecToStack \'taskkill /f /im AppMonitor.exe 2>nul\'\r\n'
    b'        Sleep 500\r\n'
    b'    ${EndIf}\r\n'
    b'    Exec "$INSTDIR\\AppMonitor.exe"\r\n'
    b'SectionEnd'
)

if old not in data:
    print("ERROR: old text not found in file")
    print("Looking for pattern...")
    idx = data.find(b'Section -PostInstall')
    if idx >= 0:
        print(f"Found at {idx}: {data[idx:idx+120]}")
    sys.exit(1)

data = data.replace(old, new)

with open(path, 'wb') as f:
    f.write(data)

print(f'OK: {path} - PostInstall section patched')
