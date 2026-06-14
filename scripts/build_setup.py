"""
Сборка установщика AppMonitor_Setup_X.X.X.exe.

1. Перемещает dist/AppMonitor.exe в dist/vX.X.X/
2. Запускает NSIS для сборки установщика
"""
import os
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(PROJECT_ROOT, "version.txt")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
NSIS_PATH = r"C:\Program Files (x86)\NSIS\makensis.exe"


def read_version() -> str:
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        return f.readline().strip()


def main():
    version = read_version()
    version_dir = os.path.join(DIST_DIR, f"v{version}")
    exe_source = os.path.join(DIST_DIR, "AppMonitor.exe")
    exe_dest = os.path.join(version_dir, "AppMonitor.exe")

    print(f"Версия: {version}")
    print(f"Папка сборки: {version_dir}")

    # 1. Создаём папку
    os.makedirs(version_dir, exist_ok=True)
    print(f"[1/3] Папка {version_dir} создана")

    # 2. Перемещаем AppMonitor.exe
    if os.path.exists(exe_source):
        shutil.move(exe_source, exe_dest)
        size_mb = os.path.getsize(exe_dest) / (1024 * 1024)
        print(f"[2/3] AppMonitor.exe перемещён ({size_mb:.2f} MB)")
    else:
        print(f"[2/3] ПРЕДУПРЕЖДЕНИЕ: {exe_source} не найден, пропускаем")

    # 3. Запускаем NSIS
    nsi_path = os.path.join(PROJECT_ROOT, "installer", "installer.nsi")
    if not os.path.exists(NSIS_PATH):
        print(f"[3/3] ОШИБКА: NSIS не найден по пути {NSIS_PATH}")
        sys.exit(1)

    print(f"[3/3] Запуск NSIS...")
    result = subprocess.run(
        [NSIS_PATH, nsi_path],
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"[3/3] ОШИБКА: NSIS завершился с кодом {result.returncode}")
        sys.exit(1)

    # Проверяем результат
    setup_path = os.path.join(version_dir, f"AppMonitor_Setup_{version}.exe")
    if os.path.exists(setup_path):
        size_mb = os.path.getsize(setup_path) / (1024 * 1024)
        print(f"[3/3] Установщик собран: {setup_path} ({size_mb:.2f} MB)")
        # Копируем установщик в корень dist/ для автообновления
        setup_dist = os.path.join(DIST_DIR, f"AppMonitor_Setup_{version}.exe")
        shutil.copy2(setup_path, setup_dist)
        print(f"[3/3] Установщик скопирован в {setup_dist} для автообновления")
    else:
        print(f"[3/3] ПРЕДУПРЕЖДЕНИЕ: установщик не найден по пути {setup_path}")
        print("Проверьте вывод NSIS выше — возможно, он лежит в другой папке")

    print("\nГотово!")


if __name__ == "__main__":
    main()
