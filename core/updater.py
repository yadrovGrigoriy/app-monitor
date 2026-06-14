"""
Модуль проверки и применения обновлений AppMonitor.

Версия приложения импортируется из core.version.APP_VERSION.
"""

import dataclasses
import glob
import logging
import os
import sys
from datetime import datetime
from core.logger import setup_logger, LOG_DIR
from core.version import APP_VERSION

logger = setup_logger('core.updater')

# Отдельный логгер для обновления — пишет в update_YYYYMMDD.log
_update_logger = logging.getLogger('update')
_update_logger.setLevel(logging.DEBUG)
if not _update_logger.handlers:
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        _update_handler = logging.FileHandler(
            os.path.join(LOG_DIR, f'update_{datetime.now().strftime("%Y%m%d")}.log'),
            encoding='utf-8'
        )
        _update_handler.setLevel(logging.DEBUG)
        _update_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        ))
        _update_logger.addHandler(_update_handler)
    except Exception as e:
        # Если не удалось создать файл лога — пишем в основной логгер
        logger.warning(f'Не удалось создать update-логгер: {e}')


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


import subprocess


def _get_latest_installer() -> str | None:
    """Найти последний установщик.

    Поиск:
    1. Рядом с exe (собранный бинарник, NSIS-установка)
    2. В папке dist/ (режим разработки)
    3. В корне проекта (режим разработки)
    4. Во временной папке PyInstaller (sys._MEIPASS)
    """
    search_dirs = []

    # 1. Рядом с exe
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        search_dirs.append(exe_dir)
        # Также проверим подпапку data/
        search_dirs.append(os.path.join(exe_dir, "data"))

    # 2. Временная папка PyInstaller
    if hasattr(sys, "_MEIPASS"):
        search_dirs.append(sys._MEIPASS)

    # 3. Папка dist/ (разработка)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dist_dir = os.path.join(project_root, "dist")
    if os.path.isdir(dist_dir):
        search_dirs.append(dist_dir)
        # Также ищем в подпапках dist/v*/
        for sub in os.listdir(dist_dir):
            sub_path = os.path.join(dist_dir, sub)
            if os.path.isdir(sub_path) and sub.startswith("v"):
                search_dirs.append(sub_path)

    # 4. Корень проекта (разработка)
    search_dirs.append(project_root)

    # Убираем дубликаты, сохраняя порядок
    seen = set()
    unique_dirs = []
    for d in search_dirs:
        if d not in seen:
            seen.add(d)
            unique_dirs.append(d)

    all_installers = []
    for d in unique_dirs:
        if not os.path.isdir(d):
            continue
        pattern = os.path.join(d, "AppMonitor_Setup_*.exe")
        found = glob.glob(pattern)
        if found:
            _update_logger.info(f"  Поиск в {d}: найдено {len(found)}")
            all_installers.extend(found)
        else:
            _update_logger.info(f"  Поиск в {d}: не найдено")

    if not all_installers:
        return None

    all_installers.sort()
    return all_installers[-1]


def _extract_version_from_filename(fname: str) -> str:
    """Извлечь версию из имени файла AppMonitor_Setup_X.X.X.exe."""
    return fname.replace("AppMonitor_Setup_", "").replace(".exe", "")


def check_local_update() -> str | None:
    """Проверить, есть ли установщик новее текущей версии рядом с exe.

    Ищет файлы AppMonitor_Setup_*.exe в папке с исполняемым файлом.
    Возвращает версию установщика, если она новее текущей, иначе None.
    """
    installer_path = _get_latest_installer()
    if not installer_path:
        return None

    fname = os.path.basename(installer_path)
    version_part = _extract_version_from_filename(fname)

    if version_part and is_newer_version(APP_VERSION, version_part):
        logger.info(f"Найден установщик новее: {fname}")
        return version_part

    return None


def apply_local_update(db=None) -> bool:
    """Запустить установщик в тихом режиме и завершить процесс.

    Ищет установщик новее текущей версии рядом с exe.
    Если находит — запускает с флагом /S (тихая установка)
    и завершает текущий процесс.

    Args:
        db: Опциональный объект Database для логирования обновления в БД.

    Возвращает True, если обновление запущено.
    """
    _ulog = _update_logger
    _ulog.info('=' * 50)
    _ulog.info('ПРОВЕРКА ОБНОВЛЕНИЯ')
    _ulog.info('=' * 50)
    _ulog.info(f'Текущая версия: {APP_VERSION}')
    _ulog.info(f'exe: {sys.executable}')
    _ulog.info(f'exe директория: {os.path.dirname(sys.executable)}')
    _ulog.info(f'frozen: {getattr(sys, "frozen", False)}')
    _ulog.info(f'_MEIPASS: {getattr(sys, "_MEIPASS", "N/A")}')

    try:
        _ulog.info('Поиск установщика...')
        installer_path = _get_latest_installer()
        _ulog.info(f'Результат поиска: {installer_path}')

        if not installer_path:
            _ulog.info('Установщик не найден, пропускаем')
            return False

        if not os.path.isfile(installer_path):
            _ulog.info(f'Установщик не является файлом: {installer_path}')
            return False

        fname = os.path.basename(installer_path)
        version_part = _extract_version_from_filename(fname)
        _ulog.info(f'Имя файла: {fname}')
        _ulog.info(f'Версия из имени: {version_part}')

        if not version_part:
            _ulog.info('Не удалось извлечь версию из имени файла')
            return False

        if not is_newer_version(APP_VERSION, version_part):
            _ulog.info(f'Версия {version_part} не новее {APP_VERSION}, пропускаем')
            return False

        _ulog.info(f'НАЙДЕНО ОБНОВЛЕНИЕ: {APP_VERSION} -> {version_part}')
        _ulog.info(f'Путь: {installer_path}')
        _ulog.info(f'Размер: {os.path.getsize(installer_path)} байт')

        # Логируем обновление в БД перед запуском установщика
        if db is not None:
            try:
                db.add_update_record(APP_VERSION, version_part)
                _ulog.info(f'Обновление записано в историю БД')
            except Exception as e:
                _ulog.warning(f'Не удалось записать обновление в БД: {e}')

        # Запускаем установщик в тихом режиме
        _ulog.info(f'Запуск установщика...')
        _ulog.info(f'Команда: {installer_path} /S /AUTORUN')

        proc = subprocess.Popen(
            [installer_path, "/S", "/AUTORUN"],
            shell=False,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _ulog.info(f'Установщик запущен, PID={proc.pid}')

        # Даём установщику время на старт
        import time
        for i in range(10):
            time.sleep(1)
            rc = proc.poll()
            if rc is not None:
                _ulog.info(f'Установщик завершился с кодом {rc} (через {i+1}с)')
                break
            _ulog.info(f'Установщик ещё работает... ({i+1}/10)')

        if proc.poll() is None:
            _ulog.info('Установщик всё ещё работает, завершаем текущий процесс')
        else:
            _ulog.info(f'Установщик завершился с кодом {proc.returncode}')

        # Завершаем текущий процесс, чтобы освободить файлы
        _ulog.info('Завершение текущего процесса...')
        _ulog.info('Вызов os._exit(0)')

        # Сбрасываем и закрываем файловые дескрипторы
        import logging
        logging.shutdown()

        os._exit(0)
    except Exception as e:
        _ulog.error(f'КРИТИЧЕСКАЯ ОШИБКА ОБНОВЛЕНИЯ: {e}', exc_info=True)
        logger.error(f'Ошибка обновления: {e}')
        return False
