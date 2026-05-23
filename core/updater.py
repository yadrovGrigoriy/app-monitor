"""
Модуль обновления AppMonitor.

Архитектура:
  1. Проверка текущей версии (из встроенной константы)
  2. Запрос к серверу обновлений Admin UI (https://192.168.3.27:8766)
  3. Скачивание нового установщика во временную папку
  4. Запуск установщика в тихом режиме и завершение текущего процесса

Проверка происходит по таймеру (каждые 60 секунд).
Если сервер недоступен — пропускаем и ждём следующую проверку.
"""

import os
import sys
import json
import tempfile
import subprocess
import dataclasses
from typing import Callable
from core.logger import setup_logger

logger = setup_logger('core.updater')

# ─── Конфигурация ────────────────────────────────────────────────────

APP_VERSION = "1.1.0"

# Адрес сервера обновлений Admin UI
ADMIN_SERVER_URL = "https://192.168.3.27:8766"

# URL для проверки обновлений
UPDATE_CHECK_URL = f"{ADMIN_SERVER_URL}/api/update/check"

# Шаблон URL для скачивания установщика
DOWNLOAD_URL_TEMPLATE = f"{ADMIN_SERVER_URL}/api/update/download/{{version}}"

# Интервал проверки обновлений (в секундах)
UPDATE_CHECK_INTERVAL_SECONDS = 60

# ─── Структуры данных ────────────────────────────────────────────────


@dataclasses.dataclass
class UpdateInfo:
    """Информация о доступном обновлении."""

    latest_version: str
    download_url: str
    release_notes: str
    is_newer: bool


# ─── HTTP-клиент (без внешних зависимостей) ──────────────────────────


def _http_get_json(url: str, timeout: int = 10) -> dict | None:
    """Выполнить HTTP GET и вернуть распарсенный JSON.

    Использует встроенные модули (urllib), чтобы не плодить зависимости.
    Отключает проверку SSL-сертификата для самоподписанных сертификатов.
    """
    import urllib.request
    import urllib.error
    import ssl

    # Создаём SSL-контекст без проверки сертификата
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AppMonitor/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        logger.warning(f"HTTP {e.code} при запросе {url}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        logger.warning(f"Ошибка сети при запросе {url}: {e.reason}")
        return None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Ошибка парсинга ответа от {url}: {e}")
        return None


def _http_download(
    url: str,
    dest_path: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> bool:
    """Скачать файл по URL в указанный путь с поддержкой прогресса."""
    import urllib.request
    import urllib.error
    import ssl

    # SSL-контекст без проверки сертификата
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AppMonitor/1.0",
        })
        with urllib.request.urlopen(req, timeout=60, context=ssl_context) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 8192

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)

            logger.info(
                f"Файл скачан: {dest_path} "
                f"({downloaded / 1024 / 1024:.1f} МБ)"
            )
            return True
    except (urllib.error.URLError, OSError) as e:
        logger.error(f"Ошибка скачивания {url}: {e}")
        return False


# ─── Версия ───────────────────────────────────────────────────────────


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Преобразовать строку версии в кортеж для сравнения.

    >>> _parse_version("1.2.3")
    (1, 2, 3)
    >>> _parse_version("1.0.0-beta")
    (1, 0, 0)
    """
    clean = version_str.split("-")[0].split("+")[0]
    parts = clean.split(".")
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            result.append(0)
    # Дополняем до 3 частей
    while len(result) < 3:
        result.append(0)
    return tuple(result[:3])


def is_newer_version(current: str, latest: str) -> bool:
    """Сравнить две версии. Вернуть True, если latest > current."""
    return _parse_version(latest) > _parse_version(current)


# ─── Основные функции ────────────────────────────────────────────────


def check_for_updates(
    current_version: str = APP_VERSION,
    update_url: str = UPDATE_CHECK_URL,
) -> UpdateInfo | None:
    """Проверить наличие обновлений на сервере Admin UI.

    Если сервер недоступен — возвращает None (пропускаем проверку).
    Возвращает UpdateInfo, если новая версия доступна, иначе None.
    """
    logger.info(f"Проверка обновлений: текущая версия {current_version}")

    data = _http_get_json(update_url)
    if data is None:
        logger.warning("Сервер обновлений недоступен, пропускаем проверку")
        return None

    latest_version = data.get("latest_version", "")
    release_notes = data.get("release_notes", "Нет описания.")
    download_url = data.get("download_url", "")

    # Если сервер не дал полный URL — формируем сами
    if download_url and download_url.startswith("/"):
        download_url = f"{ADMIN_SERVER_URL}{download_url}"
    if not download_url:
        download_url = DOWNLOAD_URL_TEMPLATE.format(version=latest_version)

    is_newer = is_newer_version(current_version, latest_version)

    logger.info(
        f"Последняя версия: {latest_version}, "
        f"текущая: {current_version}, "
        f"есть обновление: {is_newer}"
    )

    return UpdateInfo(
        latest_version=latest_version,
        download_url=download_url,
        release_notes=release_notes,
        is_newer=is_newer,
    )


def download_update(
    update_info: UpdateInfo,
    progress_callback: Callable[[int, int], None] | None = None,
) -> str | None:
    """Скачать установщик обновления во временную папку.

    Возвращает путь к скачанному файлу или None при ошибке.
    """
    logger.info(f"Скачивание обновления {update_info.latest_version}...")

    # Создаём временный файл с понятным именем
    temp_dir = tempfile.gettempdir()
    installer_name = f"AppMonitor_Setup_{update_info.latest_version}.exe"
    dest_path = os.path.join(temp_dir, installer_name)

    success = _http_download(update_info.download_url, dest_path, progress_callback)
    if success:
        logger.info(f"Обновление скачано: {dest_path}")
        return dest_path

    logger.error("Не удалось скачать обновление")
    return None


def apply_update(installer_path: str) -> None:
    """Запустить установщик в тихом режиме и завершить текущий процесс.

    Установщик NSIS запускается с флагом /S (Silent).
    После запуска текущий процесс завершается, чтобы файлы не были заняты.
    """
    logger.info(f"Запуск установщика: {installer_path}")

    try:
        subprocess.Popen(
            [installer_path, "/S"],
            shell=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        logger.info("Установщик запущен, завершаем текущий процесс")
    except OSError as e:
        logger.error(f"Не удалось запустить установщик: {e}")
        return

    # Завершаем текущий процесс
    sys.exit(0)


def clean_update(installer_path: str | None) -> None:
    """Удалить скачанный установщик после завершения обновления."""
    if installer_path and os.path.isfile(installer_path):
        try:
            os.remove(installer_path)
            logger.debug(f"Временный установщик удалён: {installer_path}")
        except OSError as e:
            logger.warning(f"Не удалось удалить временный файл: {e}")
