import sys
import os
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.database import Database
from core.monitor import ActivityMonitor
from core.autostart import AutostartManager
from core.scheduler import DailyScheduler
from api.server import AppMonitorAPI
from core.logger import setup_logger
from core.self_protect import init_self_protection, setup_watchdog

logger = setup_logger('main')

API_HOST = '0.0.0.0'
API_PORT = 8765


def main():
    logger.info('=== AppMonitor запуск ===')
    logger.info(f'Python: {sys.version}')
    logger.info(f'Platform: {sys.platform}')

    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        logger.debug('Консольное окно скрыто')
        import PyQt5.QtCore
        plugins_path = os.path.join(os.path.dirname(PyQt5.QtCore.__file__), 'Qt5', 'plugins')
        if os.path.isdir(plugins_path):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugins_path
            logger.debug(f'QT plugins path: {plugins_path}')

    # Самозащита монитора от завершения
    init_self_protection()
    setup_watchdog()

    app = QApplication(sys.argv)
    app.setApplicationName('AppMonitor')
    app.setApplicationDisplayName('Монитор активности приложений')
    app.setQuitOnLastWindowClosed(False)
    logger.info('QApplication создана')

    db = Database()
    logger.info('База данных инициализирована')

    # Запуск API-сервера для удалённого доступа (отключён)
    # api_server = AppMonitorAPI(db, host=API_HOST, port=API_PORT)
    # api_server.start()

    autostart = AutostartManager()
    if autostart.is_autostart_enabled():
        autostart.enable()
        logger.info('Автозагрузка включена')
    else:
        logger.debug('Автозагрузка не настроена')

    scheduler = DailyScheduler(db)
    scheduler.start()
    logger.info('Планировщик запущен')

    window = MainWindow(db)
    logger.info('Главное окно создано')

    monitor = ActivityMonitor(db, window)
    monitor.start()
    logger.info('Монитор активности запущен')

    logger.info('Вход в цикл событий Qt')
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
