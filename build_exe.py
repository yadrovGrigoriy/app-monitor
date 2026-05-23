"""
Сборка AppMonitor в единый EXE-файл с помощью PyInstaller.
Запуск: python build_exe.py
"""

import os
import sys
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, 'dist')
BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')
SPEC_FILE = os.path.join(PROJECT_ROOT, 'appmonitor.spec')

APP_NAME = 'AppMonitor'


def build():
    """Собрать EXE через PyInstaller."""
    print('=== Сборка AppMonitor ===')

    # Очистка предыдущей сборки
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f'Очищено: {d}')

    # Собираем команду PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        SPEC_FILE,
        '--noconfirm',
        '--clean',
        '--distpath', DIST_DIR,
        '--workpath', BUILD_DIR,
    ]

    print(f'Запуск PyInstaller...')
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f'ОШИБКА: PyInstaller завершился с кодом {result.returncode}')
        sys.exit(1)

    exe_path = os.path.join(DIST_DIR, f'{APP_NAME}.exe')
    if os.path.isfile(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f'\n✅ Сборка завершена!')
        print(f'   EXE: {exe_path}')
        print(f'   Размер: {size_mb:.1f} MB')
    else:
        print(f'\n❌ EXE не найден: {exe_path}')
        sys.exit(1)


if __name__ == '__main__':
    build()
