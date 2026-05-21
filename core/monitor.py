import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from core.database import Database
from core.limiter import Limiter
from core.logger import setup_logger

logger = setup_logger('core.monitor')


class ActivityMonitor(QObject):
    activity_updated = pyqtSignal(str, int)
    limit_reached = pyqtSignal(str, int)

    POLL_INTERVAL_MS = 1000
    SAVE_INTERVAL_SEC = 5

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.limiter = Limiter()
        self._running = False
        self._current_app = None
        self._current_title = ""
        self._elapsed_seconds = 0
        self._last_notified = {}
        logger.debug('ActivityMonitor создан')

    def _get_active_window_info(self):
        try:
            import win32gui
            import win32process
            import psutil
        except ImportError as e:
            logger.error(f'Ошибка импорта win32/psutil: {e}')
            return None
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            window_title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            app_name = process.name()
            return app_name, window_title
        except Exception as e:
            logger.debug(f'Ошибка получения окна: {e}')
            return None

    def start(self):
        if self._running:
            logger.warning('Монитор уже запущен')
            return
        self._running = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self.POLL_INTERVAL_MS)
        logger.info('Монитор активности запущен')

    def stop(self):
        self._running = False
        if hasattr(self, "_timer"):
            self._timer.stop()
        logger.info('Монитор активности остановлен')

    def _tick(self):
        info = self._get_active_window_info()
        if info is None:
            return
        app_name, window_title = info
        if not app_name or app_name.lower() in ("", "explorer.exe", "applicationframehost.exe"):
            return
        if app_name == self._current_app:
            self._elapsed_seconds += 1
        else:
            if self._current_app and self._elapsed_seconds >= self.SAVE_INTERVAL_SEC:
                logger.debug(f'Смена приложения: {self._current_app} -> {app_name} ({self._elapsed_seconds} сек)')
                self.db.update_activity(self._current_app, self._elapsed_seconds)
                self.activity_updated.emit(self._current_app, 0)
            self._current_app = app_name
            self._current_title = window_title
            self._elapsed_seconds = 0
            self.db.get_or_create_today_activity(app_name, window_title)
        if self._elapsed_seconds >= self.SAVE_INTERVAL_SEC:
            self.db.update_activity(self._current_app, self.SAVE_INTERVAL_SEC)
            self._elapsed_seconds = 0
            self.activity_updated.emit(self._current_app, 0)
            self._check_limits(app_name)

    def _check_limits(self, app_name: str):
        limit = self.db.get_limit(app_name)
        if not limit or not limit["enabled"]:
            return
        today_activity = self.db.get_or_create_today_activity(app_name)
        total_minutes = today_activity["duration_seconds"] // 60
        limit_minutes = limit["limit_minutes"]
        if total_minutes >= limit_minutes:
            now = time.time()
            last_notified = self._last_notified.get(app_name, 0)
            if now - last_notified >= 300:
                self._last_notified[app_name] = now
                logger.warning(f'Лимит {limit_minutes} мин превышен для {app_name} ({total_minutes} мин)')
                self.limit_reached.emit(app_name, limit_minutes)
            # Принудительное закрытие при превышении лимита
            self.limiter.enforce_limit(app_name, limit_minutes, total_minutes)
