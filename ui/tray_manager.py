from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QIcon
from core.notifier import Notifier

from ui.app_icon import create_app_icon


class TrayManager(QObject):
    """Управление иконкой в системном трее."""
    show_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent=None, icon: QIcon | None = None):
        super().__init__(parent)
        self.parent = parent
        self.tray_icon = None
        self.notifier = None
        self._icon = icon or create_app_icon()
        self._init_tray()

    def _cleanup_orphan_tray_icons(self):
        """Принудительно удалить все иконки AppMonitor из системного трея."""
        try:
            import ctypes
            from ctypes import wintypes

            # GUID нашей иконки (случайный, но фиксированный для приложения)
            # {A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
            guid = ctypes.create_unicode_buffer('{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}')

            NOTIFYICON_VERSION = 4
            NIM_DELETE = 2

            class NOTIFYICONDATAW(ctypes.Structure):
                _fields_ = [
                    ('cbSize', wintypes.DWORD),
                    ('hWnd', wintypes.HWND),
                    ('uID', wintypes.UINT),
                    ('uFlags', wintypes.UINT),
                    ('uCallbackMessage', wintypes.UINT),
                    ('hIcon', wintypes.HICON),
                    ('szTip', wintypes.WCHAR * 128),
                    ('dwState', wintypes.DWORD),
                    ('dwStateMask', wintypes.DWORD),
                    ('szInfo', wintypes.WCHAR * 256),
                    ('uVersion', wintypes.UINT),
                    ('szInfoTitle', wintypes.WCHAR * 64),
                    ('dwInfoFlags', wintypes.DWORD),
                    ('guidItem', wintypes.GUID),
                    ('hBalloonIcon', wintypes.HICON),
                ]

            shell32 = ctypes.windll.shell32
            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid.guidItem = guid
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        except Exception:
            pass

    def _init_tray(self):
        # Удаляем старую иконку, если была
        if self.tray_icon is not None:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()

        # Принудительно удаляем все старые иконки AppMonitor из трея
        self._cleanup_orphan_tray_icons()

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self._icon)


        tray_menu = QMenu(self.parent)
        show_action = QAction('Показать', self.parent)
        show_action.triggered.connect(self.show_requested)
        tray_menu.addAction(show_action)

        settings_action = QAction('Настройки', self.parent)
        settings_action.triggered.connect(self.settings_requested)
        tray_menu.addAction(settings_action)

        self.tray_icon.setContextMenu(tray_menu)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()

        self.notifier = Notifier(self.tray_icon)

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.show_requested.emit()

    def hide(self):
        """Скрыть иконку из трея."""
        if self.tray_icon is not None:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()
            self.tray_icon = None
