"""
Модуль версии AppMonitor.

Содержит константу APP_VERSION — единственный источник версии приложения.
При разработке читается из pyproject.toml, в собранном бинарнике — зашитая.
"""

import dataclasses
import glob
import os
import sys
from pathlib import Path
from core.logger import setup_logger

logger = setup_logger('core.updater')

# ─── Конфигурация ────────────────────────────────────────────────────

# Версия зашивается в бинарник PyInstaller'ом.
# При разработке читается из pyproject.toml.
_pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
if _pyproject.exists():
    import tomllib
    with open(_pyproject, "rb") as _f:
        _data = tomllib.load(_f)
    APP_VERSION = _data["project"]["version"]
else:
    # Запасной вариант — зашитая версия (обновляется скриптом сборки)
    APP_VERSION = "1.2.22"


# ─── Структуры данных ────────────────────────────────────────────────


@dataclasses.dataclass
class UpdateInfo:
    """Информация о доступном обновлении."""

    latest_version: str
    download_url: str
    release_notes: str
    is_newer: bool


# ─── Версия ───────────────────────────────────────────────────────────


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Преобразовать строку версии в кортеж для сравнения."""
    clean = version_str.split("-")[0].split("+")[0]
    parts = clean.split(".")
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            result.append(0)
    while len(result) < 3:
        result.append(0)
    return tuple(result[:3])


def is_newer_version(current: str, latest: str) -> bool:
    """Сравнить две версии. Вернуть True, если latest > current."""
    return _parse_version(latest) > _parse_version(current)


def check_local_update() -> str | None:
    """Проверить, есть ли установщик новее текущей версии рядом с exe.

    Ищет файлы AppMonitor_Setup_*.exe в папке с исполняемым файлом.
    Возвращает версию установщика, если она новее текущей, иначе None.
    """
    exe_dir = os.path.dirname(sys.executable)
    pattern = os.path.join(exe_dir, "AppMonitor_Setup_*.exe")
    installers = sorted(glob.glob(pattern))
    if not installers:
        return None

    latest_installer = installers[-1]
    fname = os.path.basename(latest_installer)
    # AppMonitor_Setup_1.2.24.exe -> 1.2.24
    version_part = fname.replace("AppMonitor_Setup_", "").replace(".exe", "")

    if version_part and is_newer_version(APP_VERSION, version_part):
        logger.info(f"Найден установщик новее: {fname}")
        return version_part

    return None
