import sys
import os
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.database import Database
from core.monitor import ActivityMonitor
from core.autostart import AutostartManager
from core.scheduler import DailyScheduler


def main():
    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        import PyQt5.QtCore
        plugins_path = os.path.join(os.path.dirname(PyQt5.QtCore.__file__), 'Qt5', 'plugins')
        if os.path.isdir(plugins_path):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugins_path

    app = QApplication(sys.argv)
    app.setApplicationName('AppMonitor')
    app.setApplicationDisplayName('Монитор активности приложений')
    app.setQuitOnLastWindowClosed(False)

    db = Database()
    autostart = AutostartManager()
    if autostart.is_autostart_enabled():
        autostart.enable()

    scheduler = DailyScheduler(db)
    scheduler.start()

    window = MainWindow(db)
    monitor = ActivityMonitor(db, window)
    monitor.start()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
