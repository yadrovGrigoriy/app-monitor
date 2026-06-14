"""
Сборка AppMonitor.exe через PyInstaller.
"""
import subprocess
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)

print("=" * 50)
print("Сборка AppMonitor.exe...")
print("=" * 50)

result = subprocess.run(
    [sys.executable, "-m", "PyInstaller", "AppMonitor.spec", "--noconfirm"],
    capture_output=False,
)

if result.returncode != 0:
    print(f"ОШИБКА: PyInstaller завершился с кодом {result.returncode}")
    sys.exit(1)

print("OK: AppMonitor.exe собран")
