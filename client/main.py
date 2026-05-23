"""
Точка входа для удалённого администрирования AppMonitor.
Запускает AdminUI — интерфейс для управления монитором с другого компьютера.
"""

import sys
import os

from PyQt5.QtWidgets import QApplication

from ui.admin_ui import AdminUI
from ui.theme_manager import apply_theme, THEME_DARK
from ui.app_icon import create_app_icon
from core.logger import setup_logger

logger = setup_logger('client.main')


def main():
    logger.info('=== AppMonitor Admin Client запуск ===')

    app = QApplication(sys.argv)
    app.setApplicationName('AppMonitor Admin')
    app.setApplicationDisplayName('Удалённое администрирование AppMonitor')
    app.setWindowIcon(create_app_icon())

    # Тёмная тема по умолчанию
    apply_theme(app, THEME_DARK)

    window = AdminUI()
    window.setWindowIcon(create_app_icon())
    window.show()

    logger.info('Вход в цикл событий Qt')
    try:
        exit_code = app.exec_()
    finally:
        logger.info('Завершение Admin Client')
        window.cleanup()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
