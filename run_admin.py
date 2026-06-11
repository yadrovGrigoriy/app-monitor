"""
Точка входа для удалённого администрирования AppMonitor.
Запускает AdminUI — интерфейс для управления монитором с другого компьютера.
"""

import sys
import os
import ctypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from ui.admin_ui import AdminUI
from ui.theme_manager import apply_theme, THEME_LIGHT
from ui.app_icon import create_admin_icon
from core.logger import setup_logger
from core.updater import APP_VERSION

logger = setup_logger('run_admin')

# ── Глобальный перехватчик неперехваченных исключений ──────────────
def _global_excepthook(exc_type, exc_value, exc_tb):
    """Логирует все неперехваченные исключения перед падением."""
    import traceback
    logger.critical(
        'НЕПЕРЕХВАЧЕННОЕ ИСКЛЮЧЕНИЕ: %s: %s\n%s',
        exc_type.__name__, exc_value,
        ''.join(traceback.format_tb(exc_tb))
    )
    # Вызываем оригинальный excepthook для стандартного поведения
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _global_excepthook

# ── Перенаправление stderr в logging ────────────────────────────────
import logging

class _StderrToLogging:
    """Перехватывает всё, что пишется в stderr, и направляет в лог."""
    def __init__(self, logger_: logging.Logger):
        self._logger = logger_
        self._in_log = False

    def write(self, message: str):
        if self._in_log:
            return
        message = message.rstrip()
        if message:
            self._in_log = True
            try:
                self._logger.error('STDERR: %s', message)
            finally:
                self._in_log = False

    def flush(self):
        pass

sys.stderr = _StderrToLogging(logger)


def main():
    logger.info('=== AppMonitor Admin UI запуск ===')

    app = QApplication(sys.argv)
    app.setApplicationName('AppMonitor Admin')
    app.setApplicationDisplayName('Удалённое администрирование AppMonitor')

    # Устанавливаем AppUserModelID — это заставляет Windows НЕ кэшировать
    # иконку по имени процесса (python.exe), а использовать отдельную запись
    try:
        app_id = 'AppMonitor.Admin.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        logger.debug(f'AppUserModelID установлен: {app_id}')
    except Exception as e:
        logger.warning(f'Не удалось установить AppUserModelID: {e}')

    admin_icon = create_admin_icon()
    app.setWindowIcon(admin_icon)

    apply_theme(app, THEME_LIGHT)

    window = AdminUI()
    window.setWindowIcon(admin_icon)
    window.show()

    # Запускаем Admin Update Server в фоновом потоке
    from api.admin_server import run_admin_server
    import threading
    _admin_server_thread = threading.Thread(
        target=run_admin_server,
        kwargs={'host': '0.0.0.0', 'port': 8766},
        daemon=True,
    )
    _admin_server_thread.start()
    logger.info('Admin Update Server запущен на порту 8766')

    # Фоновая проверка обновлений НЕ запускается — админка сама себе сервер обновлений.
    # Клиент (AppMonitor.exe) проверяет обновления через HTTPS к этому серверу.

    logger.info('Вход в цикл событий Qt')
    try:
        exit_code = app.exec_()
    finally:
        logger.info('Завершение Admin UI')
        window.cleanup()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
