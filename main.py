"""
Точка входа по умолчанию — запуск AppMonitor (AppUI + монитор + API + планировщик).

Для раздельного запуска используйте:
  python run_app.py      — только пользовательский интерфейс
  python run_admin.py    — удалённое администрирование (AdminUI)
  python run_server.py   — только API-сервер (без GUI)
"""

import sys
import os

# ─── Очистка lock-файла от предыдущего запуска ──────────────────────
# PyInstaller с console=False создаёт 2 процесса (загрузчик + дочерний),
# поэтому блокирующая проверка единственного экземпляра не работает.
# Просто удаляем старый lock-файл, если он есть.
import tempfile

_LOCK_FILE = os.path.join(tempfile.gettempdir(), 'AppMonitor.lock')
try:
    if os.path.exists(_LOCK_FILE):
        os.remove(_LOCK_FILE)
except Exception:
    pass

# ─── Основные импорты ────────────────────────────────────────────────

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from ui.app_ui import AppUI
from ui.theme_manager import apply_theme, THEME_LIGHT, THEME_SETTING_KEY
from ui.app_icon import create_app_icon
from core.database import Database
from core.monitor import ActivityMonitor
from core.autostart import AutostartManager
from core.scheduler import DailyScheduler
from core.updater import APP_VERSION

from api.server import AppMonitorAPI
from core.logger import setup_logger

logger = setup_logger('main')

API_HOST = '0.0.0.0'
API_PORT = 8765

# SSL-сертификаты для HTTPS (опционально)
# Поиск: рядом с main.py (разработка), рядом с exe (PyInstaller), %APPDATA%
_script_dir = os.path.dirname(os.path.abspath(__file__))
_exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else _script_dir
_appdata_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AppMonitor')

SSL_CERT_FILE = next(
    (p for p in [
        os.path.join(_exe_dir, 'cert.pem'),          # рядом с exe (NSIS установка)
        os.path.join(_exe_dir, 'data', 'cert.pem'),   # в подпапке data/
        os.path.join(_script_dir, 'data', 'cert.pem'),# разработка
        os.path.join(_appdata_dir, 'data', 'cert.pem'),# AppData
    ] if os.path.isfile(p)),
    os.path.join(_exe_dir, 'cert.pem')  # fallback
)
SSL_KEY_FILE = next(
    (p for p in [
        os.path.join(_exe_dir, 'key.pem'),           # рядом с exe (NSIS установка)
        os.path.join(_exe_dir, 'data', 'key.pem'),    # в подпапке data/
        os.path.join(_script_dir, 'data', 'key.pem'), # разработка
        os.path.join(_appdata_dir, 'data', 'key.pem'),# AppData
    ] if os.path.isfile(p)),
    os.path.join(_exe_dir, 'key.pem')  # fallback
)


def main():
    logger.info('=== AppMonitor запуск ===')
    logger.info(f'Python: {sys.version}')
    logger.info(f'Platform: {sys.platform}')

    # Удаление старых установщиков после обновления
    _cleanup_dir = _exe_dir
    try:
        for _f in os.listdir(_cleanup_dir):
            if _f.startswith('AppMonitor_Setup_') and _f.endswith('.exe'):
                fpath = os.path.join(_cleanup_dir, _f)
                try:
                    os.remove(fpath)
                    logger.info(f'Удалён установщик после обновления: {_f}')
                except Exception:
                    pass
    except Exception:
        pass

    if os.name == 'nt':
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

    # Логирование обновления: если версия изменилась — записываем в историю
    _prev_version = db.get_setting('app_version', '')
    if _prev_version and _prev_version != APP_VERSION:
        logger.info(f'Обнаружено обновление: {_prev_version} -> {APP_VERSION}')
        db.add_update_record(_prev_version, APP_VERSION)
    db.set_setting('app_version', APP_VERSION)

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

    # Фоновая проверка и автоматическое обновление (раз в 30 секунд)
    def _auto_update():
        try:
            from core.updater import apply_local_update
            apply_local_update(db)  # если есть обновление — запишет в БД, запустит установщик и завершит процесс
        except Exception as e:
            logger.debug(f'Ошибка автообновления: {e}')

    QTimer.singleShot(5000, _auto_update)
    _update_timer = QTimer()
    _update_timer.timeout.connect(_auto_update)
    _update_timer.start(30000)

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
