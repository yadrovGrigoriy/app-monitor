import datetime
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QPalette, QColor
from core.database import Database
from ui.date_toolbar import DateToolbar
from ui.activity_table import ActivityTable
from ui.bottom_bar import BottomBar
from ui.tray_manager import TrayManager
from ui.settings_dialog import SettingsDialog
from core.logger import setup_logger

logger = setup_logger('ui.main_window')


class MainWindow(QMainWindow):
    UPDATE_INTERVAL_MS = 5000

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        logger.debug('MainWindow __init__')
        self._init_ui()
        self._init_tray()
        self._init_timer()

    def _init_ui(self):
        logger.debug('Инициализация UI')
        self.setWindowTitle('Монитор активности приложений')
        self.setMinimumSize(720, 500)
        self.resize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Панель даты
        self.date_toolbar = DateToolbar()
        self.date_toolbar.date_changed.connect(self._on_date_changed)
        layout.addWidget(self.date_toolbar)

        # Таблица
        self.table = ActivityTable()
        layout.addWidget(self.table, stretch=1)

        # Нижняя панель
        self.bottom_bar = BottomBar()
        self.bottom_bar.settings_clicked.connect(self._open_settings)
        self.bottom_bar.refresh_clicked.connect(self._refresh_table)
        layout.addWidget(self.bottom_bar)

        logger.debug('UI инициализирован')

    def _init_tray(self):
        logger.debug('Инициализация трей-иконки')
        self.tray = TrayManager(self)
        self.tray.show_requested.connect(self.show_and_raise)
        self.tray.settings_requested.connect(self._open_settings)
        logger.debug('Трей-иконка создана')

    def _init_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_table)
        self._timer.start(self.UPDATE_INTERVAL_MS)

    def show_and_raise(self):
        logger.info('Показать окно (из трея)')
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_date_changed(self, qdate: QDate):
        self._refresh_table()

    def _get_activity_for_date(self, date_iso: str) -> list:
        conn = self.db._get_connection()
        try:
            rows = conn.execute(
                'SELECT * FROM activity WHERE date = ? ORDER BY duration_seconds DESC',
                (date_iso,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _refresh_table(self):
        qdate = self.date_toolbar.selected_date()
        date_iso = qdate.toString(Qt.ISODate)
        is_today = (date_iso == datetime.date.today().isoformat())

        if is_today:
            activity = self.db.get_today_activity()
        else:
            activity = self._get_activity_for_date(date_iso)

        limits = {l['app_name']: l for l in self.db.get_all_limits()}
        logger.debug(f'Обновление таблицы: {len(activity)} приложений за {date_iso}')

        self.date_toolbar.set_apps_count(len(activity))
        self.table.populate(activity, limits)

    def _open_settings(self):
        logger.info('Открытие окна настроек')
        dialog = SettingsDialog(self.db, self)
        dialog.exec_()
        logger.info('Окно настроек закрыто')
        self._refresh_table()

    def show_limit_notification(self, app_name: str, limit_minutes: int):
        logger.warning(f'Лимит превышен: {app_name} > {limit_minutes} мин')
        if self.tray.notifier:
            self.tray.notifier.show_limit_notification(app_name, limit_minutes)

    def closeEvent(self, event):
        logger.info('Попытка закрытия окна — сворачивание в трей')
        event.ignore()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F4 and event.modifiers() & Qt.AltModifier:
            logger.debug('Alt+F4 заблокирован — сворачивание в трей')
            self.hide()
            return
        super().keyPressEvent(event)
