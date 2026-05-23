"""
Полная сборка AppMonitor: иконка → EXE → установщик.
Запуск: python build_all.py

Требования:
  pip install pyinstaller pillow
  Установить NSIS (https://nsis.sourceforge.io/Download) и добавить в PATH
"""

import os
import sys
import subprocess
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, 'dist')
APP_VERSION = '1.0.0'


def step(msg: str):
    """Вывести шаг сборки."""
    print(f'\n{"=" * 60}')
    print(f'  {msg}')
    print(f'=' * 60)


def run(cmd: list, cwd: str = None) -> bool:
    """Запустить команду и вернуть True при успехе."""
    print(f'  > {" ".join(cmd)}')
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT)
    if result.returncode != 0:
        print(f'  ❌ Ошибка: код {result.returncode}')
        return False
    return True


def check_dependencies():
    """Проверить наличие необходимых инструментов."""
    step('Проверка зависимостей')

    # PyInstaller
    try:
        import PyInstaller
        print(f'  ✅ PyInstaller: {PyInstaller.__version__}')
    except ImportError:
        print('  ❌ PyInstaller не найден. Установка...')
        run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

    # Pillow
    try:
        from PIL import Image
        print(f'  ✅ Pillow: {Image.__version__}')
    except ImportError:
        print('  ❌ Pillow не найден. Установка...')
        run([sys.executable, '-m', 'pip', 'install', 'pillow'])

    # NSIS
    nsis_paths = [
        r'C:\Program Files (x86)\NSIS\makensis.exe',
        r'C:\Program Files\NSIS\makensis.exe',
    ]
    nsis_found = False
    for p in nsis_paths:
        if os.path.isfile(p):
            print(f'  ✅ NSIS: {p}')
            nsis_found = True
            break
    if not nsis_found:
        # Проверяем через PATH
        nsis_in_path = shutil.which('makensis')
        if nsis_in_path:
            print(f'  ✅ NSIS: {nsis_in_path}')
            nsis_found = True
        else:
            print('  ⚠️  NSIS не найден. Установщик не будет создан.')
            print('     Скачайте: https://nsis.sourceforge.io/Download')
            print('     Или соберите .exe вручную: python build_exe.py')

    return nsis_found


def generate_icon():
    """Сгенерировать .ico файл."""
    step('Генерация иконки')
    ico_path = os.path.join(PROJECT_ROOT, 'app_icon.ico')
    if os.path.isfile(ico_path):
        print(f'  ✅ Иконка уже существует: {ico_path}')
        return True
    return run([sys.executable, 'generate_icon.py'])


def build_exe():
    """Собрать EXE через PyInstaller."""
    step('Сборка EXE через PyInstaller')
    return run([sys.executable, 'build_exe.py'])


def build_installer():
    """Собрать установщик через NSIS."""
    step('Сборка установщика через NSIS')

    # Путь к makensis
    nsis_paths = [
        r'C:\Program Files (x86)\NSIS\makensis.exe',
        r'C:\Program Files\NSIS\makensis.exe',
    ]
    makensis = None
    for p in nsis_paths:
        if os.path.isfile(p):
            makensis = p
            break
    if not makensis:
        makensis = shutil.which('makensis')
    if not makensis:
        print('  ❌ NSIS не найден')
        return False

    # Копируем иконку в dist для NSIS
    ico_src = os.path.join(PROJECT_ROOT, 'app_icon.ico')
    ico_dst = os.path.join(DIST_DIR, 'app_icon.ico')
    if os.path.isfile(ico_src):
        shutil.copy2(ico_src, ico_dst)

    # Копируем LICENSE.txt в dist
    license_src = os.path.join(PROJECT_ROOT, 'LICENSE.txt')
    license_dst = os.path.join(DIST_DIR, 'LICENSE.txt')
    if os.path.isfile(license_src):
        shutil.copy2(license_src, license_dst)

    # Копируем NSIS-скрипт в dist
    nsi_src = os.path.join(PROJECT_ROOT, 'installer.nsi')
    nsi_dst = os.path.join(DIST_DIR, 'installer.nsi')
    shutil.copy2(nsi_src, nsi_dst)

    # Запускаем makensis из dist (чтобы пути совпадали)
    result = run([makensis, nsi_dst], cwd=DIST_DIR)

    # Ищем установщик
    installer_name = f'AppMonitor_Setup_{APP_VERSION}.exe'
    installer_path = os.path.join(DIST_DIR, installer_name)
    if os.path.isfile(installer_path):
        size_mb = os.path.getsize(installer_path) / (1024 * 1024)
        print(f'\n  ✅ Установщик создан: {installer_path}')
        print(f'     Размер: {size_mb:.1f} MB')
    else:
        print(f'  ⚠️  Установщик не найден: {installer_path}')
        print('     Проверьте, что NSIS установлен корректно.')

    return result


def main():
    """Полная сборка."""
    print(f'\n{"=" * 60}')
    print(f'  ПОЛНАЯ СБОРКА AppMonitor v{APP_VERSION}')
    print(f'  Проект: {PROJECT_ROOT}')
    print(f'=' * 60)

    # Шаг 1: Проверка зависимостей
    nsis_available = check_dependencies()

    # Шаг 2: Генерация иконки
    if not generate_icon():
        print('❌ Ошибка генерации иконки')
        sys.exit(1)

    # Шаг 3: Сборка EXE
    if not build_exe():
        print('❌ Ошибка сборки EXE')
        sys.exit(1)

    # Шаг 4: Сборка установщика (опционально)
    if nsis_available:
        build_installer()
    else:
        print(f'\n  ✅ EXE собран: {os.path.join(DIST_DIR, "AppMonitor.exe")}')
        print('  ⚠️  Установщик не создан — NSIS не найден.')
        print('     Установите NSIS: https://nsis.sourceforge.io/Download')
        print('     Затем запустите: makensis dist\\installer.nsi')

    print(f'\n{"=" * 60}')
    print(f'  СБОРКА ЗАВЕРШЕНА')
    print(f'  Результаты в: {DIST_DIR}')
    print(f'=' * 60)


if __name__ == '__main__':
    main()
