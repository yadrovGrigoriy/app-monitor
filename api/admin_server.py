"""
Отдельный FastAPI-сервер для Admin UI.

Предоставляет API для:
  - Проверки обновлений AppMonitor
  - Скачивания установщика новой версии
  - Получения информации о последней версии

Запускается на отдельном порту (по умолчанию 8766) параллельно с основным API.
"""

import os
import json
import logging
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.logger import setup_logger

logger = setup_logger('api.admin_server')

# ─── Конфигурация ────────────────────────────────────────────────────

APP_VERSION = "1.2.6"
APP_NAME = "AppMonitor"

# Путь к папке с установщиками (собираются скриптом build_installer.ps1)
DIST_DIR = Path(__file__).resolve().parent.parent / "dist"

# ─── Схемы ───────────────────────────────────────────────────────────


class UpdateCheckResponse(BaseModel):
    """Ответ на запрос проверки обновления."""

    latest_version: str
    current_version: str
    has_update: bool
    download_url: str
    release_notes: str
    release_date: str | None = None


class UpdateDownloadResponse(BaseModel):
    """Ответ на запрос скачивания установщика."""

    filename: str
    version: str
    size_bytes: int


# ─── Приложение ──────────────────────────────────────────────────────

app = FastAPI(
    title=f"{APP_NAME} Admin Update Server",
    version=APP_VERSION,
    description="Сервер обновлений для удалённого администрирования AppMonitor",
)


def _find_installer(version: str | None = None) -> Path | None:
    """Найти установщик в папке dist или dist/vX.X.X.

    Ищет файл по шаблону AppMonitor_Setup_{version}.exe.
    Сначала в dist/, потом в dist/vX.X.X/.
    Если version не указан — ищет последний по версии.
    """
    if not DIST_DIR.exists():
        logger.warning(f"Папка dist не найдена: {DIST_DIR}")
        return None

    import re

    def _search_in_dir(directory: Path, ver: str | None) -> Path | None:
        """Поиск установщика в конкретной папке."""
        if not directory.exists():
            return None

        if ver:
            candidate = directory / f"AppMonitor_Setup_{ver}.exe"
            if candidate.exists():
                return candidate
            return None

        # Ищем последний по версии
        best_version = (0, 0, 0)
        best_path = None

        for f in directory.glob("AppMonitor_Setup_*.exe"):
            match = re.search(r"AppMonitor_Setup_([\d.]+)\.exe", f.name)
            if match:
                try:
                    v = tuple(int(x) for x in match.group(1).split("."))
                    if v > best_version:
                        best_version = v
                        best_path = f
                except ValueError:
                    continue

        return best_path

    # Сначала ищем в dist/
    result = _search_in_dir(DIST_DIR, version)
    if result:
        return result

    # Если не нашли — ищем в dist/vX.X.X/
    if version:
        result = _search_in_dir(DIST_DIR / f"v{version}", version)
        if result:
            return result
    else:
        # Ищем последнюю версию среди всех папок dist/v*/
        best_version = (0, 0, 0)
        best_path = None

        for folder in DIST_DIR.glob("v*/"):
            match = re.search(r"v([\d.]+)$", folder.name)
            if match:
                try:
                    v = tuple(int(x) for x in match.group(1).split("."))
                    if v > best_version:
                        best_version = v
                        best_path = folder
                except ValueError:
                    continue

        if best_path:
            result = _search_in_dir(best_path, None)
            if result:
                return result

        # Если и в папках не нашли — ищем в dist/ ещё раз (на случай если dist/ пуст, а папки есть)
        result = _search_in_dir(DIST_DIR, None)
        if result:
            return result

    logger.warning(f"Установщик{' для версии ' + version if version else ''} не найден")
    return None


def _get_release_notes() -> str:
    """Получить описание последней версии из CHANGELOG или pyproject.toml."""
    changelog = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
    if changelog.exists():
        try:
            content = changelog.read_text("utf-8")
            # Берём первый блок после заголовка версии
            lines = content.split("\n")
            notes = []
            capture = False
            for line in lines:
                if line.startswith(f"## {APP_VERSION}"):
                    capture = True
                    continue
                if capture:
                    if line.startswith("## "):
                        break
                    if line.strip():
                        notes.append(line.strip())
            return "\n".join(notes[:20]) if notes else "Список изменений недоступен."
        except Exception as e:
            logger.warning(f"Ошибка чтения CHANGELOG: {e}")

    return "Автоматическое обновление AppMonitor."


# ─── Эндпоинты ───────────────────────────────────────────────────────


@app.get("/api/update/check", response_model=UpdateCheckResponse)
def check_update():
    """Проверить наличие новой версии.

    Клиент (AppMonitor) присылает свою версию в заголовке X-App-Version.
    Если заголовок отсутствует — возвращаем информацию о последней версии.
    """
    # Версия клиента не нужна — сервер всегда отдаёт последнюю доступную
    installer = _find_installer()
    if installer is None:
        raise HTTPException(
            status_code=404,
            detail="Установщик не найден на сервере. Соберите проект через build_installer.ps1",
        )

    # Извлекаем версию из имени файла
    import re

    match = re.search(r"AppMonitor_Setup_([\d.]+)\.exe", installer.name)
    latest_version = match.group(1) if match else APP_VERSION

    return UpdateCheckResponse(
        latest_version=latest_version,
        current_version=APP_VERSION,
        has_update=True,
        download_url=f"/api/update/download/{latest_version}",
        release_notes=_get_release_notes(),
        release_date=datetime.fromtimestamp(installer.stat().st_mtime).isoformat(),
    )


@app.get("/api/update/download/{version}")
def download_update(version: str):
    """Скачать установщик указанной версии."""
    installer = _find_installer(version)
    if installer is None:
        raise HTTPException(
            status_code=404,
            detail=f"Установщик версии {version} не найден. "
                   f"Доступные версии: {', '.join(f.name for f in DIST_DIR.glob('AppMonitor_Setup_*.exe'))}",
        )

    return FileResponse(
        path=str(installer),
        filename=installer.name,
        media_type="application/x-msdownload",
        headers={
            "Content-Disposition": f'attachment; filename="{installer.name}"',
        },
    )


@app.get("/api/update/versions")
def list_versions():
    """Список всех доступных версий установщиков."""
    versions = []
    for f in sorted(DIST_DIR.glob("AppMonitor_Setup_*.exe"), reverse=True):
        import re

        match = re.search(r"AppMonitor_Setup_([\d.]+)\.exe", f.name)
        if match:
            versions.append({
                "version": match.group(1),
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return {"versions": versions, "count": len(versions)}


@app.get("/api/status")
def status():
    """Статус сервера обновлений."""
    installer = _find_installer()
    latest_version = None
    if installer:
        import re

        match = re.search(r"AppMonitor_Setup_([\d.]+)\.exe", installer.name)
        latest_version = match.group(1) if match else None

    return {
        "status": "ok",
        "server": f"{APP_NAME} Admin Update Server",
        "version": APP_VERSION,
        "latest_installer": latest_version,
        "installers_count": len(list(DIST_DIR.glob("AppMonitor_Setup_*.exe"))),
        "platform": platform.system(),
        "hostname": platform.node(),
    }


# ─── Запуск ──────────────────────────────────────────────────────────


def run_admin_server(host: str = "0.0.0.0", port: int = 8766):
    """Запустить сервер обновлений для Admin UI.

    Args:
        host: Хост для привязки (по умолчанию 0.0.0.0 — все интерфейсы)
        port: Порт (по умолчанию 8766)
    """
    logger.info(f"Запуск Admin Update Server на {host}:{port}")
    logger.info(f"Папка с установщиками: {DIST_DIR}")

    # Проверяем, есть ли установщики
    installers = list(DIST_DIR.glob("AppMonitor_Setup_*.exe"))
    if not installers:
        logger.warning(
            "Установщики не найдены! Соберите проект:\n"
            "  python scripts/build_installer.ps1\n"
            "  или\n"
            "  pyinstaller AppMonitor.spec && makensis installer/installer.nsi"
        )
    else:
        logger.info(f"Найдено установщиков: {len(installers)}")
        for inst in installers:
            logger.info(f"  {inst.name} ({inst.stat().st_size / 1024 / 1024:.1f} МБ)")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        ssl_keyfile=None,  # HTTP (без HTTPS для простоты)
        ssl_certfile=None,
    )


if __name__ == "__main__":
    run_admin_server()
