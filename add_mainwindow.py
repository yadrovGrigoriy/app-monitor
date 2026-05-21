import os, json
base = "C:/Users/Григорий/code/AppMonitor"
json_path = os.path.join(base, "project_files.json")
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

data["ui/main_window.py"] = """from PyQt5.QtWidgets import (
    QMainWindow, QSystemTrayIcon, QMenu, QAction,
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QLabel,
    QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from core.database import Database
from core.notifier import Notifier
from ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    UPDATE_INTERVAL_MS = 5000

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.notifier = Notifier()
        self._init_ui()
        self._init_tray()
        self._init_timer()

    def _init_ui(self):
        self.setWindowTitle('Монитор активности')
        self.setMinimumSize(600, 400)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        title = QLabel('Активность приложений за сегодня')
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Приложение', 'Время', 'Лимит'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        btn_layout = QHBoxLayout()
        btn_settings = QPushButton('Настройки')
        btn_settings.clicked.connect(self._open_settings)
        btn_layout.addWidget(btn_settings)
        btn_refresh = QPushButton('Обновить')
        btn_refresh.clicked.connect(self._refresh_table)
        btn_layout.addWidget(btn_refresh)
        btn_quit = QPushButton('Выйти')
        btn_quit.clicked.connect(QApplication.instance().quit)
        btn_layout.addWidget(btn_quit)
        layout.addLayout(btn_layout)

    def _init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        self.tray_icon.setToolTip('AppMonitor')
        tray_menu = QMenu()
        show_action = QAction('Показать', self)
        show_action.triggered.connect(self.show_and_raise)
        tray_menu.addAction(show_action)
        settings_action = QAction('Настройки', self)
        settings_action.triggered.connect(self._open_settings)
        tray_menu.addAction(settings_action)
        tray_menu.addSeparator()
        quit_action = QAction('Выйти', self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        self.notifier = Notifier(self.tray_icon)

    def _init_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_table)
        self._timer.start(self.UPDATE_INTERVAL_MS)

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_and_raise()

    def _refresh_table(self):
        activity = self.db.get_today_activity()
        limits = {l['app_name']: l for l in self.db.get_all_limits()}
        self.table.setRowCount(len(activity))
        for i, item in enumerate(activity):
            self.table.setItem(i, 0, QTableWidgetItem(item['app_name']))
            hours = item['duration_seconds'] // 3600
            minutes = (item['duration_seconds'] % 3600) // 60
            time_str = f'{hours} ч {minutes:02d} мин'
            self.table.setItem(i, 1, QTableWidgetItem(time_str))
            limit = limits.get(item['app_name'])
            if limit and limit['enabled']:
                limit_str = f'{limit["limit_minutes"]} мин'
                if item['duration_seconds'] // 60 >= limit['limit_minutes']:
                    limit_str += ' (!)'
            else:
                limit_str = 'нет'
            self.table.setItem(i, 2, QTableWidgetItem(limit_str))

    def _open_settings(self):
        dialog = SettingsDialog(self.db, self)
        dialog.exec_()
        self._refresh_table()

    def show_limit_notification(self, app_name: str, limit_minutes: int):
        self.notifier.show_limit_notification(app_name, limit_minutes)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
"""

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)
print("OK")
