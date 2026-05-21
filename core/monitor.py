import time
import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from core.database import Database
from core.limiter import Limiter
from core.logger import setup_logger

logger = setup_logger('core.monitor')


class ActivityMonitor(QObject):
    activity_updated = pyqtSignal(str, int)
    limit_reached = pyqtSignal(str, int)

    POLL_INTERVAL_MS = 1000
    SAVE_INTERVAL_SEC = 10

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.limiter = Limiter()
        self._running = False
        self._last_notified = {}
        self._excluded_cache: set[str] = set()
        self._excluded_cache_time = 0
        logger.debug('ActivityMonitor created')

    def _get_app_name(self, process, window_title: str) -> tuple[str, str]:
        """Return (display_name, system_id).
        display_name — human-readable name for display.
        system_id — process name (process.name()), used for exclusion checks.
        """
        system_id = process.name().lower()
        display_name = system_id

        try:
            import win32api
            exe_path = process.exe()
            lang, codepage = win32api.GetFileVersionInfo(exe_path, '\\VarFileInfo\\Translation')[0]
            file_desc = win32api.GetFileVersionInfo(
                exe_path, f'\\StringFileInfo\\{lang:04X}{codepage:04X}\\FileDescription'
            )
            if file_desc:
                display_name = file_desc
        except Exception:
            pass

        # Fallback: if process is python.exe, try to extract IDE name from window title
        # Only triggers if FileDescription didn't return a readable name
        if system_id in ('python.exe', 'pythonw.exe'):
            need_fallback = (
                display_name == system_id
                or '\\' in display_name or '/' in display_name
            )
            if need_fallback:
                if window_title:
                    for kw in ('PyCharm', 'IntelliJ', 'CLion', 'WebStorm', 'PhpStorm',
                               'GoLand', 'Rider', 'DataGrip', 'RubyMine', 'AppCode',
                               'VS Code', 'Code', 'Sublime Text', 'Notepad++', 'Vim',
                               'Neovim', 'Emacs', 'Terminal', 'cmd', 'PowerShell',
                               'Windows PowerShell', 'MINGW', 'Git Bash', 'WSL',
                               'Jupyter', 'JupyterLab', 'Spyder', 'RStudio',
                               'MATLAB', 'Mathematica', 'Maple',
                               'Qt Designer', 'Qt Creator', 'Android Studio',
                               'Xcode', 'Visual Studio', 'VSCodium'):
                        if kw.lower() in window_title.lower():
                            return kw, system_id
                    for sep in (' — ', ' - ', ' – ', ' — ', ' | ', ' :: '):
                        if sep in window_title:
                            parts = window_title.split(sep, 1)
                            second = parts[1].strip()
                            for kw in ('PyCharm', 'IntelliJ', 'CLion', 'WebStorm',
                                       'PhpStorm', 'GoLand', 'Rider', 'DataGrip',
                                       'RubyMine', 'AppCode', 'VS Code', 'Code',
                                       'Sublime Text', 'Notepad++', 'Vim', 'Neovim',
                                       'Emacs', 'Terminal', 'cmd', 'PowerShell',
                                       'Windows PowerShell', 'MINGW', 'Git Bash',
                                       'WSL', 'Jupyter', 'JupyterLab', 'Spyder',
                                       'RStudio', 'MATLAB', 'Mathematica', 'Maple',
                                       'Qt Designer', 'Qt Creator', 'Android Studio',
                                       'Xcode', 'Visual Studio', 'VSCodium'):
                                if kw.lower() in second.lower():
                                    return kw, system_id
                            return parts[0].strip(), system_id
                return 'Python', system_id
        return display_name, system_id

    def _get_active_window_info(self):
        """Return list of (app_name, window_title) for all open windows."""
        try:
            import win32gui
            import win32process
            import psutil
        except ImportError as e:
            logger.error(f'Failed to import win32/psutil: {e}')
            return []

        windows = []
        seen_pids = set()

        def _enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            window_title = win32gui.GetWindowText(hwnd)
            if not window_title:
                return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid in seen_pids:
                    return
                seen_pids.add(pid)
                process = psutil.Process(pid)
                display_name, system_id = self._get_app_name(process, window_title)
                if self._is_excluded(system_id):
                    return
                windows.append((display_name, system_id, window_title))
            except Exception:
                pass

        win32gui.EnumWindows(_enum_callback, None)
        return windows

    def _is_excluded(self, system_id: str) -> bool:
        """Check if app is excluded from tracking.
        Caches exclusion list for 30 seconds.
        """
        import time
        now = time.time()
        if now - self._excluded_cache_time > 30:
            self._refresh_excluded_cache()
        return system_id in self._excluded_cache

    def _refresh_excluded_cache(self):
        """Force refresh the exclusion cache."""
        import time
        self._excluded_cache = {e['system_id'].lower() for e in self.db.get_excluded_apps()}
        self._excluded_cache_time = time.time()

    def start(self):
        if self._running:
            logger.warning('Monitor already running')
            return
        self._running = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self.POLL_INTERVAL_MS)
        logger.info('Activity monitor started')

    def stop(self):
        self._running = False
        if hasattr(self, "_timer"):
            self._timer.stop()
        logger.info('Activity monitor stopped')

    def _tick(self):
        logger.debug('_tick called')
        try:
            import win32gui
            import win32process
            import psutil
            fg_hwnd = win32gui.GetForegroundWindow()
            fg_title = win32gui.GetWindowText(fg_hwnd)
            _, fg_pid = win32process.GetWindowThreadProcessId(fg_hwnd)
            fg_process = psutil.Process(fg_pid)
            fg_app_name, fg_system_id = self._get_app_name(fg_process, fg_title)
            logger.debug(f'Active window: hwnd={fg_hwnd} title="{fg_title}" pid={fg_pid} app={fg_app_name} sys={fg_system_id}')
            if self._is_excluded(fg_system_id):
                logger.debug(f'{fg_system_id} is excluded, skipping')
                fg_app_name = None
        except Exception as e:
            logger.error(f'Failed to get active window: {e}')
            fg_app_name = None
            fg_title = ''

        if not fg_app_name:
            logger.debug('fg_app_name is None, exiting')
            return

        # Save +1s to DB and update UI — single connection
        self.db.tick_activity(fg_app_name, fg_title, fg_system_id)
        self.activity_updated.emit(fg_system_id, 0)

        # Check limits every 10 seconds
        now = time.time()
        if now - self._last_notified.get('_last_limit_check', 0) >= 10:
            self._last_notified['_last_limit_check'] = now
            self._check_limits(fg_system_id)

        logger.debug(f'TICK: sys={fg_system_id}')

    def _check_limits(self, system_id: str):
        limit = self.db.get_limit_by_system_id(system_id)
        if not limit or not limit["enabled"]:
            return
        db_row = self.db.get_or_create_today_activity_by_system_id(system_id)
        db_duration = db_row["duration_seconds"] if db_row else 0
        total_minutes = db_duration // 60
        limit_minutes = limit["limit_minutes"]
        if total_minutes >= limit_minutes:
            now = time.time()
            last_notified = self._last_notified.get(system_id, 0)
            if now - last_notified >= 300:
                self._last_notified[system_id] = now
                logger.warning(f'Limit {limit_minutes} min exceeded for {system_id} ({total_minutes} min)')
                self.limit_reached.emit(system_id, limit_minutes)
