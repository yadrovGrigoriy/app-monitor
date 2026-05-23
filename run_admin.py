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
from core.updater import APP_VERSION, UPDATE_CHECK_INTERVAL_SECONDS

logger = setup_logger('run_admin')


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

    # Фоновая проверка обновлений (первая через 5 секунд, затем каждые 60)
    from PyQt5.QtCore import QTimer
    from ui.dialogs.update_dialog import _check_updates_background

    QTimer.singleShot(5000, _check_updates_background)
    _update_timer = QTimer()
    _update_timer.timeout.connect(_check_updates_background)
    _update_timer.start(UPDATE_CHECK_INTERVAL_SECONDS * 1000)

    logger.info('Вход в цикл событий Qt')
    try:
        exit_code = app.exec_()
    finally:
        logger.info('Завершение Admin UI')
        window.cleanup()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
