"""
Полная сборка AppMonitor.

1. patch_nsi  — генерация installer.nsi из шаблона (версия из version.txt)
2. build_exe  — сборка AppMonitor.exe через PyInstaller
3. build_setup — сборка установщика через NSIS + копирование в dist/

Использование:
    python scripts/build_all.py
"""

import os
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(PROJECT_ROOT, "version.txt")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "installer", "installer.template.nsi")
OUTPUT_NSI = os.path.join(PROJECT_ROOT, "installer", "installer.nsi")
NSIS_PATH = r"C:\Program Files (x86)\NSIS\makensis.exe"


def read_version() -> str:
    """Прочитать и автоматически повысить версию из version.txt.

    Увеличивает patch (последнюю цифру) на 1 при каждом запуске.
    Пример: 1.2.60 -> 1.2.61
    """
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            version = f.readline().strip()
            if not version:
                print("ОШИБКА: version.txt пуст")
                sys.exit(1)
            if not re.match(r"^\d+\.\d+\.\d+$", version):
                print(f"ОШИБКА: неверный формат версии в version.txt: '{version}'")
                sys.exit(1)

            # Повышаем patch-версию
            major, minor, patch = version.split(".")
            new_version = f"{major}.{minor}.{int(patch) + 1}"

            # Обновляем version.txt
            with open(VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(new_version)

            print(f"Версия повышена: {version} -> {new_version}")
            return new_version
    except FileNotFoundError:
        print(f"ОШИБКА: файл {VERSION_FILE} не найден")
        sys.exit(1)


def step_patch_nsi(version: str) -> None:
    """Шаг 1: генерация installer.nsi из шаблона."""
    print("\n" + "=" * 50)
    print(f"ШАГ 1/3: Генерация installer.nsi (версия {version})")
    print("=" * 50)

    if not os.path.exists(TEMPLATE_PATH):
        print(f"ОШИБКА: шаблон {TEMPLATE_PATH} не найден")
        sys.exit(1)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    content = template.replace("__VERSION__", version)

    with open(OUTPUT_NSI, "w", encoding="cp1251") as f:
        f.write(content)

    print(f"OK: {OUTPUT_NSI} сгенерирован (кодировка cp1251)")


def step_build_exe() -> None:
    """Шаг 2: сборка AppMonitor.exe через PyInstaller."""
    print("\n" + "=" * 50)
    print("ШАГ 2/3: Сборка AppMonitor.exe")
    print("=" * 50)

    os.chdir(PROJECT_ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "AppMonitor.spec", "--noconfirm"],
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"ОШИБКА: PyInstaller завершился с кодом {result.returncode}")
        sys.exit(1)

    print("OK: AppMonitor.exe собран")


def step_build_setup(version: str) -> None:
    """Шаг 3: сборка установщика через NSIS."""
    print("\n" + "=" * 50)
    print(f"ШАГ 3/3: Сборка установщика (версия {version})")
    print("=" * 50)

    version_dir = os.path.join(DIST_DIR, f"v{version}")
    exe_source = os.path.join(DIST_DIR, "AppMonitor.exe")
    exe_dest = os.path.join(version_dir, "AppMonitor.exe")

    # 3.1 Создаём папку
    os.makedirs(version_dir, exist_ok=True)
    print(f"[3.1] Папка {version_dir} создана")

    # 3.2 Перемещаем AppMonitor.exe
    if os.path.exists(exe_source):
        shutil.move(exe_source, exe_dest)
        size_mb = os.path.getsize(exe_dest) / (1024 * 1024)
        print(f"[3.2] AppMonitor.exe перемещён ({size_mb:.2f} MB)")
    else:
        print(f"[3.2] ПРЕДУПРЕЖДЕНИЕ: {exe_source} не найден, пропускаем")

    # 3.3 Запускаем NSIS
    if not os.path.exists(NSIS_PATH):
        print(f"[3.3] ОШИБКА: NSIS не найден по пути {NSIS_PATH}")
        sys.exit(1)

    print(f"[3.3] Запуск NSIS...")
    result = subprocess.run([NSIS_PATH, OUTPUT_NSI], capture_output=False)

    if result.returncode != 0:
        print(f"[3.3] ОШИБКА: NSIS завершился с кодом {result.returncode}")
        sys.exit(1)

    # 3.4 Проверяем результат
    setup_path = os.path.join(version_dir, f"AppMonitor_Setup_{version}.exe")
    if os.path.exists(setup_path):
        size_mb = os.path.getsize(setup_path) / (1024 * 1024)
        print(f"[3.4] Установщик собран: {setup_path} ({size_mb:.2f} MB)")
        # Копируем в корень dist/ для автообновления
        setup_dist = os.path.join(DIST_DIR, f"AppMonitor_Setup_{version}.exe")
        shutil.copy2(setup_path, setup_dist)
        print(f"[3.4] Установщик скопирован в {setup_dist} для автообновления")
    else:
        print(f"[3.4] ПРЕДУПРЕЖДЕНИЕ: установщик не найден по пути {setup_path}")


def main():
    print("=" * 50)
    print("ПОЛНАЯ СБОРКА AppMonitor")
    print("=" * 50)

    version = read_version()
    print(f"Версия: {version}")

    step_patch_nsi(version)
    step_build_exe()
    step_build_setup(version)

    print("\n" + "=" * 50)
    print("СБОРКА ЗАВЕРШЕНА УСПЕШНО!")
    print("=" * 50)
    print(f"  dist/AppMonitor.exe")
    print(f"  dist/v{version}/AppMonitor_Setup_{version}.exe")
    print(f"  dist/AppMonitor_Setup_{version}.exe")


if __name__ == "__main__":
    main()
