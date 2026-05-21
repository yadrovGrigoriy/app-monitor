"""
Принудительное закрытие приложений при превышении лимита времени.
Использует win32 API для отправки сигнала закрытия окна.
"""

import time
import logging
from typing import Optional

logger = logging.getLogger('core.limiter')

# Приложения, которые НЕЛЬЗЯ принудительно закрывать
PROTECTED_PROCESSES = frozenset({
    'explorer.exe',
    'svchost.exe',
    'csrss.exe',
    'winlogon.exe',
    'services.exe',
    'lsass.exe',
    'System',
    'Idle',
    'taskmgr.exe',  # чтобы пользователь мог снять блокировку
    # Сам монитор — нельзя закрыть принудительно
    'appmonitor.exe',
    'app_monitor.exe',
    'python.exe',
    'pythonw.exe',
})

# Задержка между повторными попытками закрытия (сек)
RETRY_DELAY_SEC = 10
# Сколько раз пытаемся закрыть перед тем как сдаться
MAX_RETRIES = 3


class Limiter:
    """
    Отслеживает превышение лимитов и принудительно закрывает приложения.
    """

    def __init__(self):
        self._closed_apps: dict[str, float] = {}  # app_name -> время последнего закрытия
        self._retry_count: dict[str, int] = {}  # app_name -> число попыток
        logger.debug('Limiter создан')

    def enforce_limit(self, app_name: str, limit_minutes: int, current_minutes: int) -> bool:
        """
        Проверить, превышен ли лимит, и если да — закрыть приложение.

        Returns:
            True если приложение было закрыто, False если нет.
        """
        if current_minutes < limit_minutes:
            # Лимит не превышен — сбрасываем счётчики
            self._closed_apps.pop(app_name, None)
            self._retry_count.pop(app_name, None)
            return False

        if app_name.lower() in PROTECTED_PROCESSES:
            logger.warning(f'Попытка закрыть защищённый процесс: {app_name}')
            return False

        now = time.time()
        last_closed = self._closed_apps.get(app_name, 0.0)

        # Если недавно уже закрывали — пропускаем (anti-flood)
        if now - last_closed < RETRY_DELAY_SEC:
            return False

        retries = self._retry_count.get(app_name, 0)
        if retries >= MAX_RETRIES:
            logger.warning(
                f'Исчерпаны попытки закрыть {app_name} ({retries}), '
                f'пользователь {limit_minutes} мин превышен на {current_minutes - limit_minutes} мин'
            )
            return False

        logger.warning(
            f'Принудительное закрытие {app_name} (лимит {limit_minutes} мин, '
            f'использовано {current_minutes} мин, попытка {retries + 1}/{MAX_RETRIES})'
        )

        closed = self._close_app(app_name)
        if closed:
            self._closed_apps[app_name] = now
            self._retry_count[app_name] = retries + 1
        return closed

    def _close_app(self, app_name: str) -> bool:
        """
        Закрыть приложение по имени процесса.
        Сначала пытается вежливо (WM_CLOSE), затем kill.
        """
        try:
            import win32gui
            import win32process
            import win32con
            import psutil
        except ImportError as e:
            logger.error(f'Не удалось импортировать win32/psutil: {e}')
            return False

        try:
            # Ищем все окна, принадлежащие процессу с таким именем
            closed_any = False

            def _enum_callback(hwnd, _hwnds):
                nonlocal closed_any
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc = psutil.Process(pid)
                    if proc.name().lower() == app_name.lower():
                        # Пробуем вежливо закрыть
                        logger.debug(f'Отправка WM_CLOSE окну {hwnd} ({app_name})')
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        closed_any = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                except Exception as e:
                    logger.debug(f'Ошибка при закрытии окна {hwnd}: {e}')

            win32gui.EnumWindows(_enum_callback, None)

            if not closed_any:
                # Если окна не нашлись — убиваем процесс
                logger.debug(f'Окна не найдены, убиваем процесс {app_name}')
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'] and proc.info['name'].lower() == app_name.lower():
                            proc.terminate()
                            closed_any = True
                            logger.debug(f'Процесс {app_name} (PID {proc.info["pid"]}) завершён')
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            return closed_any

        except Exception as e:
            logger.error(f'Ошибка при закрытии {app_name}: {e}')
            return False

    def reset(self, app_name: Optional[str] = None):
        """Сбросить счётчики попыток для приложения (или для всех)."""
        if app_name:
            self._closed_apps.pop(app_name, None)
            self._retry_count.pop(app_name, None)
        else:
            self._closed_apps.clear()
            self._retry_count.clear()
        logger.debug(f'Счётчики limiter сброшены: {app_name or "все"}')
