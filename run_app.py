"""
Точка входа для пользовательского интерфейса AppMonitor.
Запускает AppUI + монитор активности + API-сервер + планировщик.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.app_ui import AppUI
from ui.theme_manager import apply_theme, THEME_LIGHT, THEME_SETTING_KEY
from ui.app_icon import create_app_icon
from core.database import Database
from core.monitor import ActivityMonitor
from core.autostart import AutostartManager
from core.scheduler import DailyScheduler
from api.server import AppMonitorAPI
from core.logger import setup_logger

logger = setup_logger('run_app')

API_HOST = '0.0.0.0'
API_PORT = 8765
SSL_CERT_FILE = os.path.join(os.path.dirname(__file__), 'data', 'cert.pem')
SSL_KEY_FILE = os.path.join(os.path.dirname(__file__), 'data', 'key.pem')
MUTEX_NAME = r'Global\AppMonitor_SingleInstance'


def _check_single_instance() -> bool:
    try:
        import psutil
        import time
        current_pid = os.getpid()
        current_exe = sys.executable.lower()
        current_create_time = psutil.Process(current_pid).create_time()
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'create_time']):
            try:
                pid = proc.info['pid']
                if pid == current_pid:
                    continue
                exe = (proc.info['exe'] or '').lower()
                if exe != current_exe:
                    continue
                name = (proc.info['name'] or '').lower()
                if name not in ('python.exe', 'pythonw.exe'):
                    continue
                cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                if 'main.py' not in cmdline and 'run_app.py' not in cmdline:
                    continue
                proc_create_time = proc.info['create_time']
                if proc_create_time and current_create_time - proc_create_time > 1.0:
                    logger.info(f'Убиваем старый процесс PID={pid} (запущен раньше)')
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        import win32event
        import win32api
        import winerror
        mutex = win32event.CreateMutex(None, False, MUTEX_NAME)
        last_error = win32api.GetLastError()
        if last_error == winerror.ERROR_ALREADY_EXISTS:
            logger.warning('Mutex занят, ждём освобождения...')
            for _ in range(30):
                time.sleep(0.2)
                win32api.CloseHandle(mutex)
                mutex = win32event.CreateMutex(None, False, MUTEX_NAME)
                last_error = win32api.GetLastError()
                if last_error != winerror.ERROR_ALREADY_EXISTS:
                    logger.info('Mutex освобождён, продолжаем')
                    return True
            logger.error('Не удалось дождаться освобождения mutex')
            return False
        else:
            logger.info(f'Первый запуск (mutex создан, last_error={last_error})')
            return True
    except ImportError:
        logger.warning('win32api/psutil не доступен, проверка единственного экземпляра пропущена')
        return True


def main():
    logger.info('=== AppMonitor (AppUI) запуск ===')
    logger.info(f'Python: {sys.version}')
    logger.info(f'Platform: {sys.platform}')

    if not _check_single_instance():
        logger.error('Не удалось убить старый экземпляр, завершение')
        QMessageBox.critical(None, 'Ошибка', 'Не удалось убить старый экземпляр AppMonitor!')
        sys.exit(1)

    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        logger.debug('Консольное окно скрыто')
        import PyQt5.QtCore
        plugins_path = os.path.join(os.path.dirname(PyQt5.QtCore.__file__), 'Qt5', 'plugins')
        if os.path.isdir(plugins_path):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugins_path
            logger.debug(f'QT plugins path: {plugins_path}')

    app = QApplication(sys.argv)
    app.setApplicationName('AppMonitor')
    app.setApplicationDisplayName('Монитор активности приложений')
    app.setWindowIcon(create_app_icon())

    if os.name == 'nt':
        try:
            import ctypes
            app_id = 'AppMonitor.Monitor.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            logger.debug(f'AppUserModelID установлен: {app_id}')
        except Exception as e:
            logger.warning(f'Не удалось установить AppUserModelID: {e}')
    app.setQuitOnLastWindowClosed(False)
    app.aboutToQuit.connect(lambda: None)

    logger.info('QApplication создана')
    db = Database()
    logger.info('База данных инициализирована')

    saved_theme = db.get_setting(THEME_SETTING_KEY, THEME_LIGHT)
    apply_theme(app, saved_theme)

    ssl_cert = SSL_CERT_FILE if os.path.isfile(SSL_CERT_FILE) else None
    ssl_key = SSL_KEY_FILE if os.path.isfile(SSL_KEY_FILE) else None
    if ssl_cert and ssl_key:
        logger.info('SSL-сертификаты найдены, API будет работать по HTTPS')
    else:
        logger.info('SSL-сертификаты не найдены, API работает по HTTP')

    api_server = AppMonitorAPI(db, host=API_HOST, port=API_PORT,
                                ssl_certfile=ssl_cert, ssl_keyfile=ssl_key)
    api_server.start()

    autostart = AutostartManager()
    if autostart.is_autostart_enabled():
        autostart.enable()
    else:
        logger.debug('Автозагрузка не настроена')

    scheduler = DailyScheduler(db)
    scheduler.start()
    logger.info('Планировщик запущен')

    monitor = ActivityMonitor(db)
    window = AppUI(db, monitor)
    window.setWindowIcon(create_app_icon())
    logger.info('Главное окно создано')

    monitor.start()
    window._refresh_all()
    window.show()

    logger.info('Вход в цикл событий Qt')
    try:
        exit_code = app.exec_()
    finally:
        logger.info('Завершение AppMonitor')
        monitor.stop()
        scheduler.stop()
        window.cleanup()
        db.close()
        logger.info('AppMonitor завершён')
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
