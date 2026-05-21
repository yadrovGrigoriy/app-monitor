from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtCore import pyqtSignal, QObject
from core.notifier import Notifier


class TrayManager(QObject):
    """Управление иконкой в системном трее."""
    show_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.tray_icon = None
        self.notifier = None
        self._init_tray()

    def _init_tray(self):
        # Удаляем старую иконку, если была
        if self.tray_icon is not None:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.parent.style().standardIcon(self.parent.style().SP_ComputerIcon))
        self.tray_icon.setToolTip('AppMonitor')

        tray_menu = QMenu(self)
        show_action = QAction('Показать', self)
        show_action.triggered.connect(self.show_requested)
        tray_menu.addAction(show_action)

        settings_action = QAction('Настройки', self)
        settings_action.triggered.connect(self.settings_requested)
        tray_menu.addAction(settings_action)

        tray_menu.addSeparator()
        quit_action = QAction('Выйти', self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()

        self.notifier = Notifier(self.tray_icon)

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.show_requested.emit()
