"""
Модуль версии AppMonitor.

Единственный источник версии — файл version.txt в корне проекта (при разработке)
или рядом с AppMonitor.exe (в собранном бинарнике).
"""

import os
import sys

_VERSION_FILE = "version.txt"


def _read_version_from_file(filepath: str) -> str | None:
    """Прочитать версию из текстового файла."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            line = f.readline().strip()
            if line:
                return line
    except (FileNotFoundError, PermissionError, OSError):
        pass
    return None


def _get_version() -> str:
    """
    Определить версию приложения.

    Приоритет:
    1. version.txt во временной папке PyInstaller (sys._MEIPASS)
    2. version.txt рядом с exe (собранный бинарник, если запущен не через PyInstaller)
    3. version.txt в корне проекта (разработка)
    4. Запасная версия (если ничего не найдено)
    """
    # 1. Рядом с exe (приоритет — сюда установщик кладёт version.txt)
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        ver = _read_version_from_file(os.path.join(exe_dir, _VERSION_FILE))
        if ver:
            return ver

    # 2. Временная папка PyInstaller (sys._MEIPASS) — запасной вариант
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        ver = _read_version_from_file(os.path.join(sys._MEIPASS, _VERSION_FILE))
        if ver:
            return ver

    # 3. В корне проекта (разработка)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ver = _read_version_from_file(os.path.join(project_root, _VERSION_FILE))
    if ver:
        return ver

    # 4. Запасной вариант
    return "1.0.0"


APP_VERSION = _get_version()
