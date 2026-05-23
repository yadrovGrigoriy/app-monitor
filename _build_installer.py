"""
Сборка EXE-установщика AppMonitor.
Создаёт AppMonitor_Setup.exe, который при запуске устанавливает AppMonitor в систему.

Запуск: python _build_installer.py
"""

import os
import sys
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, 'dist')
BUILD_DIR = os.path.join(PROJECT_ROOT, 'build_installer')


def build_installer():
    """Собрать installer.exe через PyInstaller."""
    print('=== Сборка установщика AppMonitor ===')

    # Очистка
    for d in [BUILD_DIR]:
        if os.path.isdir(d):
            shutil.rmtree(d)
    # Переименовываем старый установщик, если есть
    old_installer = os.path.join(DIST_DIR, 'AppMonitor_Setup.exe')
    if os.path.isfile(old_installer):
        try:
            os.remove(old_installer)
            print(f'  Удалён старый установщик')
        except Exception:
            # Если заблокирован — переименовываем
            import uuid
            renamed = old_installer + '.' + uuid.uuid4().hex[:8] + '.old'
            try:
                os.rename(old_installer, renamed)
                print(f'  Старый установщик переименован: {renamed}')
            except Exception as e2:
                print(f'  Не удалось удалить/переименовать старый установщик: {e2}')
                print('  Возможно, он запущен. Закройте его и повторите.')
                return False

    # Создаём временную папку для сборки установщика
    tmp_dir = os.path.join(PROJECT_ROOT, '_installer_src')
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)

    # Копируем скрипт установщика
    installer_py = os.path.join(tmp_dir, 'installer.py')
    src_installer_py = os.path.join(PROJECT_ROOT, '_installer_main.py')
    shutil.copy2(src_installer_py, installer_py)

    # Копируем AppMonitor.exe рядом со скриптом
    src_exe = os.path.join(DIST_DIR, 'AppMonitor.exe')
    dst_exe = os.path.join(tmp_dir, 'AppMonitor.exe')
    if os.path.isfile(src_exe):
        shutil.copy2(src_exe, dst_exe)
        exe_size = os.path.getsize(dst_exe) / (1024 * 1024)
        print(f'  AppMonitor.exe скопирован ({exe_size:.1f} MB)')
    else:
        print(f'  ❌ AppMonitor.exe не найден в {DIST_DIR}')
        return False

    # Собираем installer.exe
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--name', 'AppMonitor_Setup',
        '--distpath', DIST_DIR,
        '--workpath', BUILD_DIR,
        '--noconfirm',
        '--clean',
        '--add-data', f'{dst_exe}{os.pathsep}.',
        installer_py,
    ]

    print('  Запуск PyInstaller...')
    result = subprocess.run(cmd, cwd=tmp_dir)
    if result.returncode != 0:
        print(f'  ❌ Ошибка PyInstaller: код {result.returncode}')
        return False

    # Результат уже в DIST_DIR
    installer_path = os.path.join(DIST_DIR, 'AppMonitor_Setup.exe')
    if os.path.isfile(installer_path):
        size_mb = os.path.getsize(installer_path) / (1024 * 1024)
        print(f'\n  ✅ Установщик создан: {installer_path}')
        print(f'     Размер: {size_mb:.1f} MB')
    else:
        print(f'  ❌ Установщик не найден: {installer_path}')
        return False

    # Очистка временных файлов
    shutil.rmtree(tmp_dir, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)

    return True


if __name__ == '__main__':
    build_installer()
