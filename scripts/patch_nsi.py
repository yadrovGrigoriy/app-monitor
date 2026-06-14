"""
Генерация installer.nsi из шаблона installer.template.nsi.

Версия читается из version.txt (единственный источник правды).
Путь к папке сборки формируется автоматически из версии.

Использование:
    python scripts/patch_nsi.py
"""

import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "installer", "installer.template.nsi")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "installer", "installer.nsi")
VERSION_FILE = os.path.join(PROJECT_ROOT, "version.txt")


def read_version() -> str:
    """Прочитать версию из version.txt."""
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            version = f.readline().strip()
            if not version:
                print("ОШИБКА: version.txt пуст")
                sys.exit(1)
            if not re.match(r"^\d+\.\d+\.\d+$", version):
                print(f"ОШИБКА: неверный формат версии в version.txt: '{version}'")
                sys.exit(1)
            return version
    except FileNotFoundError:
        print(f"ОШИБКА: файл {VERSION_FILE} не найден")
        sys.exit(1)


def generate_nsi(version: str) -> None:
    """Сгенерировать installer.nsi из шаблона, подставив версию."""
    if not os.path.exists(TEMPLATE_PATH):
        print(f"ОШИБКА: шаблон {TEMPLATE_PATH} не найден")
        sys.exit(1)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    content = template.replace("__VERSION__", version)

    with open(OUTPUT_PATH, "w", encoding="cp1251") as f:
        f.write(content)

    print(f"OK: {OUTPUT_PATH} сгенерирован (версия {version}, кодировка cp1251)")


if __name__ == "__main__":
    version = read_version()
    generate_nsi(version)
