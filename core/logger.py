import logging
import sys
import os
from datetime import datetime

# Приоритет: %APPDATA%\AppMonitor\logs (всегда, т.к. туда гарантированно есть доступ на запись)
_APPDATA_BASE = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AppMonitor')

LOG_DIR = os.path.join(_APPDATA_BASE, 'logs')
LOG_FILE = os.path.join(LOG_DIR, f'appmonitor_{datetime.now().strftime("%Y%m%d")}.log')
APP_LOG_FILE = os.path.join(LOG_DIR, f'app_{datetime.now().strftime("%Y%m%d")}.log')
UPDATE_LOG_FILE = os.path.join(LOG_DIR, f'update_{datetime.now().strftime("%Y%m%d")}.log')


def setup_logger(name: str) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Имена прикладных логгеров (мониторинг, трекер)
    _app_loggers = {'core.monitor', 'ui.base_ui', 'ui.app_ui', 'ui.admin_ui'}

    root = logging.getLogger()
    if not root.handlers:
        # Файловый handler — системные логи
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        file_handler.setFormatter(file_fmt)
        root.addHandler(file_handler)

        # Файловый handler — прикладные логи (мониторинг, трекер)
        app_handler = logging.FileHandler(APP_LOG_FILE, encoding='utf-8')
        app_handler.setLevel(logging.DEBUG)
        app_fmt = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        app_handler.setFormatter(app_fmt)
        app_handler.addFilter(_AppLogFilter(_app_loggers))
        root.addHandler(app_handler)

        # Консольный handler — DEBUG и выше
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_fmt = logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_fmt)
        root.addHandler(console_handler)

    logger.propagate = True
    return logger


class _AppLogFilter(logging.Filter):
    """Пропускает только сообщения от прикладных логгеров."""
    def __init__(self, app_loggers: set):
        super().__init__()
        self._app_loggers = app_loggers

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name in self._app_loggers
