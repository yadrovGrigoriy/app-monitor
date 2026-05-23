"""
Создание дистрибутива AppMonitor: ZIP-архив с EXE и батниками.
"""
import os
import shutil
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, 'dist')
OUTPUT_ZIP = os.path.join(PROJECT_ROOT, 'AppMonitor_v1.0.0.zip')

def main():
    print('=== Создание дистрибутива AppMonitor ===')

    # Проверяем, что EXE существует
    exe_path = os.path.join(DIST_DIR, 'AppMonitor.exe')
    if not os.path.isfile(exe_path):
        print(f'❌ EXE не найден: {exe_path}')
        print('Сначала запустите сборку: python _do_build.py')
        return

    # Файлы для архива
    files_to_zip = [
        ('AppMonitor.exe', os.path.join(DIST_DIR, 'AppMonitor.exe')),
        ('install.bat', os.path.join(DIST_DIR, 'install.bat')),
        ('uninstall.bat', os.path.join(DIST_DIR, 'uninstall.bat')),
    ]

    # Создаём ZIP
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
        for arcname, src_path in files_to_zip:
            if os.path.isfile(src_path):
                zf.write(src_path, arcname)
                print(f'  Добавлен: {arcname}')

    size_mb = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
    print(f'\n✅ Дистрибутив создан: {OUTPUT_ZIP}')
    print(f'   Размер: {size_mb:.1f} MB')
    print(f'\n📦 Для установки:')
    print(f'   1. Распакуйте ZIP')
    print(f'   2. Запустите install.bat от имени администратора')


if __name__ == '__main__':
    main()
