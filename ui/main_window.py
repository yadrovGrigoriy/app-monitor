import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QApplication, QDialog,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QHBoxLayout, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QColor, QCursor
from PyQt5.QtWidgets import QMenu, QAction
from core.database import Database
from ui.widgets.date_toolbar import DateToolbar
from ui.widgets.activity_table import ActivityTable
from ui.widgets.tracked_table import TrackedTable
from ui.widgets.bottom_bar import BottomBar
from ui.tray_manager import TrayManager
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.limit_dialog import AddLimitDialog
from ui.dialogs.stats_dialog import StatsDialog
from ui.styles import MAIN_WINDOW_INPUT_STYLE, COLOR_DANGER
from ui.breadcrumbs import breadcrumb_title, component_tooltip
from core.logger import setup_logger

logger = setup_logger('ui.main_window')

COLOR_TEXT_SECONDARY = "#616161"

STYLE_TAB_TABLE = """
    QTableWidget {
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        font-size: 13px;
    }
    QTableWidget::item {
        padding: 6px 12px;
    }
    QHeaderView::section {
        font-weight: 600;
        padding: 6px 12px;
        border: none;
        border-bottom: 1px solid #e0e0e0;
    }
"""


class MainWindow(QMainWindow):
    UPDATE_INTERVAL_MS = 5000
    WARNING_NOTIFY_INTERVAL_MIN = 5
    MAX_EXTENSION_TOTAL = 15
    EXTENSION_STEP = 5
    # Интервал обновления счётчика активного приложения на вкладке 1 (мс)
    ACTIVE_TICK_INTERVAL_MS = 1000

    def __init__(self, db: Database, monitor=None):
        super().__init__()
        self.db = db
        self._monitor = monitor
        self._settings_authorized = True
        self._notified_warning: set[str] = set()
        self._last_exceeded_notify: dict[str, datetime.datetime] = {}
        self._extensions: dict[str, int] = {}
        logger.debug('MainWindow __init__')
        self._init_ui()
        self._init_tray()
        self._init_timer()
        self._init_active_timer()
        self._connect_monitor_signals()

    def _init_ui(self):
        logger.debug('Инициализация UI')
        self.setWindowTitle(breadcrumb_title('Главная'))
        self.setMinimumSize(720, 500)
        self.resize(900, 600)
        self.setStyleSheet(MAIN_WINDOW_INPUT_STYLE)

        central = QWidget()
        central.setToolTip(component_tooltip(self))
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # Панель даты
        self.date_toolbar = DateToolbar()
        self.date_toolbar.date_changed.connect(self._on_date_changed)
        self.date_toolbar.period_changed.connect(self._on_period_changed)
        layout.addWidget(self.date_toolbar)

        # Вкладки
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, stretch=1)

        # ── Вкладка 1: Открытые приложения ──────────────────────────
        self.open_tab = QWidget()
        open_layout = QVBoxLayout(self.open_tab)
        open_layout.setContentsMargins(0, 4, 0, 4)
        self.open_table = QTableWidget()
        self.open_table.setColumnCount(4)
        self.open_table.setHorizontalHeaderLabels(['Имя процесса', 'Приложение', 'Окно', 'Время'])
        self.open_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.open_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.open_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.open_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.open_table.setAlternatingRowColors(True)
        self.open_table.setShowGrid(False)
        self.open_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.open_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.open_table.verticalHeader().setVisible(False)
        self.open_table.setStyleSheet(STYLE_TAB_TABLE)
        self.open_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.open_table.customContextMenuRequested.connect(self._on_open_context_menu)
        self.open_table.cellDoubleClicked.connect(self._on_open_double_click)
        open_layout.addWidget(self.open_table, stretch=1)
        self.tabs.addTab(self.open_tab, 'Открытые приложения')

        # ── Вкладка 2: Отслеживаются ────────────────────────────────
        self.tracked_tab = QWidget()
        tracked_layout = QVBoxLayout(self.tracked_tab)
        tracked_layout.setContentsMargins(0, 4, 0, 4)
        self.tracked_table = TrackedTable()
        self.tracked_table.remove_requested.connect(self._remove_tracked)
        self.tracked_table.add_limit_requested.connect(self._add_limit_from_tracked)
        tracked_layout.addWidget(self.tracked_table, stretch=1)
        self.tabs.addTab(self.tracked_tab, 'Отслеживаются')

        # ── Вкладка 3: Исключения ───────────────────────────────────
        self.excluded_tab = QWidget()
        excluded_layout = QVBoxLayout(self.excluded_tab)
        excluded_layout.setContentsMargins(0, 4, 0, 4)
        excluded_layout.setSpacing(8)

        self.excluded_table = QTableWidget()
        self.excluded_table.setColumnCount(3)
        self.excluded_table.setHorizontalHeaderLabels(['Имя процесса', 'Отображаемое имя', ''])
        self.excluded_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.excluded_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.excluded_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.excluded_table.setAlternatingRowColors(True)
        self.excluded_table.setShowGrid(False)
        self.excluded_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.excluded_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.excluded_table.verticalHeader().setVisible(False)
        self.excluded_table.setStyleSheet(STYLE_TAB_TABLE)
        self.excluded_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.excluded_table.customContextMenuRequested.connect(self._on_excluded_context_menu)
        excluded_layout.addWidget(self.excluded_table, stretch=1)

        btn_row = QHBoxLayout()
        btn_add_exclude = QPushButton('Добавить исключение')
        btn_add_exclude.setFixedHeight(32)
        btn_add_exclude.clicked.connect(self._add_exclude_dialog)
        btn_row.addWidget(btn_add_exclude)
        btn_row.addStretch()
        excluded_layout.addLayout(btn_row)

        self.tabs.addTab(self.excluded_tab, 'Исключения')

        # Нижняя панель
        self.bottom_bar = BottomBar()
        self.bottom_bar.settings_clicked.connect(self._open_settings)
        self.bottom_bar.stats_clicked.connect(self._open_stats)
        self.bottom_bar.refresh_clicked.connect(self._refresh_all)
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
        self._timer.timeout.connect(self._refresh_all)
        self._timer.start(self.UPDATE_INTERVAL_MS)

    def _init_active_timer(self):
        """Таймер для обновления активной вкладки каждую секунду."""
        self._active_timer = QTimer(self)
        self._active_timer.timeout.connect(self._tick_active_app)
        self._active_timer.start(self.ACTIVE_TICK_INTERVAL_MS)

    def _connect_monitor_signals(self):
        """Подключить сигналы монитора к обработчикам UI."""
        pass  # Сигналы монитора не используем — обновляемся по таймеру

    def show_and_raise(self):
        logger.info('Показать окно (из трея)')
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_date_changed(self, qdate: QDate):
        self._refresh_tracked_tab()

    def _on_period_changed(self, period: str):
        self._refresh_tracked_tab()

    # ── Открытые приложения ─────────────────────────────────────────

    def _get_open_windows(self) -> list[dict]:
        """Вернуть список открытых окон, исключая исключённые приложения."""
        if not self._monitor:
            return []
        try:
            import win32gui
            import win32process
            import psutil
        except ImportError:
            return []

        excluded = {e['system_id'].lower() for e in self.db.get_excluded_apps()}
        windows = []
        seen_pids = set()

        def _enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid in seen_pids:
                    return
                seen_pids.add(pid)
                process = psutil.Process(pid)
                sys_id = process.name()
                if sys_id.lower() in excluded:
                    return
                display_name = sys_id
                try:
                    import win32api
                    exe_path = process.exe()
                    lang, codepage = win32api.GetFileVersionInfo(
                        exe_path, '\\VarFileInfo\\Translation'
                    )[0]
                    file_desc = win32api.GetFileVersionInfo(
                        exe_path, f'\\StringFileInfo\\{lang:04X}{codepage:04X}\\FileDescription'
                    )
                    if file_desc:
                        display_name = file_desc
                except Exception:
                    pass
                windows.append({'display_name': display_name, 'system_id': sys_id, 'title': title})
            except Exception:
                pass

        win32gui.EnumWindows(_enum_callback, None)
        return windows

    def _get_active_system_id(self) -> str | None:
        """Вернуть system_id активного (foreground) окна или None."""
        try:
            import win32gui
            import win32process
            fg_hwnd = win32gui.GetForegroundWindow()
            if not fg_hwnd:
                return None
            _, pid = win32process.GetWindowThreadProcessId(fg_hwnd)
            import psutil
            process = psutil.Process(pid)
            return process.name()
        except Exception:
            return None

    def _tick_active_app(self):
        """Каждую секунду обновлять время на активной вкладке."""
        current = self.tabs.currentIndex()
        if current == 0:
            # Вкладка «Открытые приложения» — обновляем время для всех строк
            for row in range(self.open_table.rowCount()):
                sys_item = self.open_table.item(row, 0)
                if sys_item:
                    self._update_open_tab_time_for(sys_item.text().lower())
        elif current == 1:
            # Вкладка «Отслеживаются» — обновляем время для всех строк
            for row in range(self.tracked_table.rowCount()):
                sys_item = self.tracked_table.item(row, 0)
                if sys_item:
                    self._update_tracked_tab_time_for(row, sys_item.text().lower())

    def _update_open_tab_time_for(self, sys_id_lower: str):
        """Обновить отображение времени для конкретного приложения на вкладке 1."""
        today = datetime.date.today().isoformat()
        conn = self.db._get_connection()
        try:
            row = conn.execute(
                'SELECT duration_seconds FROM activity WHERE date = ? AND LOWER(system_id) = ?',
                (today, sys_id_lower)
            ).fetchone()
            duration = row['duration_seconds'] if row else 0
        finally:
            conn.close()

        hours = duration // 3600
        minutes = (duration % 3600) // 60
        secs = duration % 60
        time_str = f'{hours}:{minutes:02d}:{secs:02d}'

        for row in range(self.open_table.rowCount()):
            item = self.open_table.item(row, 0)
            if item and item.text().lower() == sys_id_lower:
                time_item = self.open_table.item(row, 3)
                if time_item:
                    time_item.setText(time_str)
                break

    def _update_tracked_tab_time_for(self, row: int, system_id: str):
        """Обновить время, лимит и остаток для строки на вкладке «Отслеживаются»."""
        today = datetime.date.today().isoformat()
        conn = self.db._get_connection()
        try:
            row_data = conn.execute(
                'SELECT duration_seconds, app_name FROM activity WHERE date = ? AND LOWER(system_id) = ?',
                (today, system_id)
            ).fetchone()
            duration = row_data['duration_seconds'] if row_data else 0
            app_name = row_data['app_name'] if row_data else system_id
        finally:
            conn.close()

        # Время
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        secs = duration % 60
        time_str = f'{hours}:{minutes:02d}:{secs:02d}'
        time_item = self.tracked_table.item(row, 2)
        if time_item:
            time_item.setText(time_str)

        # Лимит и остаток
        limits = {l['app_name']: l for l in self.db.get_all_limits()}
        limit = limits.get(app_name)

        # Колонка 3 — лимит
        limit_item = self.tracked_table.item(row, 3)
        if limit_item and limit and limit['enabled']:
            exceeded = duration // 60 >= limit['limit_minutes']
            limit_str = f'{limit["limit_minutes"]} мин'
            if exceeded:
                limit_str += ' ⚠'
                limit_item.setForeground(QColor(COLOR_DANGER))
                limit_item.setBackground(QColor(COLOR_DANGER + '20'))
            else:
                limit_item.setForeground(QColor('#107c10'))
                limit_item.setBackground(QColor('#ffffff'))
            limit_item.setText(limit_str)

        # Колонка 4 — остаток
        remaining_item = self.tracked_table.item(row, 4)
        if remaining_item and limit and limit['enabled']:
            used = duration // 60
            left = max(0, limit['limit_minutes'] - used)
            remaining_item.setText(f'{left} мин')
            if left == 0:
                remaining_item.setForeground(QColor(COLOR_DANGER))
            else:
                remaining_item.setForeground(QColor('#107c10'))

    def _refresh_open_tab(self):
        """Обновить вкладку открытых приложений."""
        windows = self._get_open_windows()
        today = datetime.date.today().isoformat()
        conn = self.db._get_connection()
        try:
            # Все записи активности за сегодня (для отображения времени)
            activity_rows = conn.execute(
                'SELECT system_id, duration_seconds FROM activity WHERE date = ? '
                'AND system_id IS NOT NULL AND system_id != \'\'',
                (today,)
            ).fetchall()
            activity = {r['system_id'].lower(): r['duration_seconds'] for r in activity_rows}
            # Только отслеживаемые (для подсветки)
            tracked_rows = conn.execute(
                'SELECT system_id FROM activity WHERE date = ? AND is_tracked = 1 '
                'AND system_id IS NOT NULL AND system_id != \'\'',
                (today,)
            ).fetchall()
            tracked_set = {r['system_id'].lower() for r in tracked_rows}
        finally:
            conn.close()

        # Сортируем по убыванию времени
        windows_sorted = sorted(
            windows,
            key=lambda w: activity.get(w['system_id'].lower(), 0),
            reverse=True
        )

        self.open_table.setRowCount(len(windows_sorted))
        for i, w in enumerate(windows_sorted):
            sys_id_lower = w['system_id'].lower()
            is_tracked = sys_id_lower in tracked_set
            duration = activity.get(sys_id_lower, 0)

            sys_item = QTableWidgetItem(w['system_id'])
            sys_item.setForeground(QColor('#000000'))
            self.open_table.setItem(i, 0, sys_item)

            name_item = QTableWidgetItem(w['display_name'])
            name_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.open_table.setItem(i, 1, name_item)

            title_item = QTableWidgetItem(w['title'])
            title_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.open_table.setItem(i, 2, title_item)

            # Время — показываем для всех приложений, даже не отслеживаемых
            # Для отслеживаемых — из БД, для остальных — 0 (будет расти если активно)
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            secs = duration % 60
            time_str = f'{hours}:{minutes:02d}:{secs:02d}'
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignCenter)
            time_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.open_table.setItem(i, 3, time_item)

            # Помечаем отслеживаемые приложения
            if is_tracked:
                for col in range(4):
                    item = self.open_table.item(i, col)
                    if item:
                        item.setBackground(QColor('#e8f5e9'))  # светло-зелёный

        self.open_table.resizeRowsToContents()
        logger.debug(f'Обновление открытых приложений: {len(windows)} окон')

    def _on_open_double_click(self, row: int, column: int):
        """По двойному клику — перейти на вкладку отслеживаемых и выделить строку."""
        sys_id_item = self.open_table.item(row, 0)
        if not sys_id_item:
            return
        sys_id = sys_id_item.text()

        # Найти app_name по system_id в activity
        today = datetime.date.today().isoformat()
        conn = self.db._get_connection()
        try:
            row_data = conn.execute(
                'SELECT app_name FROM activity WHERE date = ? AND system_id = ?',
                (today, sys_id)
            ).fetchone()
        finally:
            conn.close()

        if not row_data:
            return

        app_name = row_data['app_name']

        # Переключиться на вкладку отслеживаемых (индекс 1)
        self.tabs.setCurrentIndex(1)

        # Найти и выделить строку с этим app_name
        for r in range(self.tracked_table.rowCount()):
            item = self.tracked_table.item(r, 1)
            if item and item.text() == app_name:
                self.tracked_table.selectRow(r)
                self.tracked_table.scrollToItem(item)
                break

    def _on_open_context_menu(self, pos):
        """Контекстное меню для открытых приложений."""
        row = self.open_table.rowAt(pos.y())
        if row < 0:
            return
        sys_id = self.open_table.item(row, 0).text()
        display_name = self.open_table.item(row, 1).text()

        # Проверяем, отслеживается ли приложение
        today = datetime.date.today().isoformat()
        conn = self.db._get_connection()
        try:
            row_data = conn.execute(
                'SELECT is_tracked FROM activity WHERE date = ? AND system_id = ?',
                (today, sys_id)
            ).fetchone()
            is_tracked = row_data is not None and row_data['is_tracked'] == 1
        finally:
            conn.close()

        menu = QMenu(self)

        if not is_tracked:
            action_track = QAction('Добавить для отслеживания', self)
            action_track.triggered.connect(
                lambda: self._add_track_from_open(sys_id, display_name)
            )
            menu.addAction(action_track)

        action_exclude = QAction('Исключить', self)
        action_exclude.triggered.connect(
            lambda: self._exclude_from_table(sys_id, display_name)
        )
        menu.addAction(action_exclude)

        menu.exec_(QCursor.pos())

    # ── Отслеживаются ──────────────────────────────────────────────

    def _add_track_from_open(self, system_id: str, display_name: str):
        """Добавить приложение для отслеживания из вкладки открытых приложений."""
        logger.info(f'Добавление для отслеживания: {system_id} ({display_name})')
        self.db.mark_as_tracked(display_name, system_id)
        self._refresh_all()

    def _add_limit_from_tracked(self, app_name: str):
        """Добавить лимит для отслеживаемого приложения."""
        logger.info(f'Добавление лимита из отслеживаемых: {app_name}')
        dialog = AddLimitDialog(self.db, self, preset_app=app_name)
        if dialog.exec_() == QDialog.Accepted and dialog.app_name:
            self.db.set_limit(dialog.app_name, dialog.limit_minutes, True)
            self._refresh_tracked_tab()

    def _remove_tracked(self, system_id: str):
        """Удалить приложение из отслеживания."""
        logger.info(f'Удаление из отслеживания: {system_id}')
        reply = QMessageBox.question(
            self, 'Удаление из отслеживания',
            f'Убрать "{system_id}" из списка отслеживаемых?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.mark_as_untracked(system_id)
            self._refresh_all()

    def _exclude_from_table(self, system_id: str, display_name: str):
        logger.info(f'Исключение приложения: {system_id} ({display_name})')
        self.db.add_excluded_app(system_id, display_name)
        if self._monitor:
            self._monitor._refresh_excluded_cache()
        self._refresh_all()

    def _refresh_tracked_tab(self):
        """Обновить вкладку отслеживаемых приложений."""
        today = datetime.date.today().isoformat()
        items = self.db.get_tracked_activity(today)
        limits = {l['app_name']: l for l in self.db.get_all_limits()}
        self.tracked_table.populate(items, limits)
        logger.debug(f'Обновление отслеживаемых: {len(items)} приложений')

    # ── Исключения ──────────────────────────────────────────────────

    def _refresh_excluded_tab(self):
        """Обновить вкладку исключений."""
        excluded = self.db.get_excluded_apps()
        self.excluded_table.setRowCount(len(excluded))
        for i, item in enumerate(excluded):
            sys_item = QTableWidgetItem(item['system_id'])
            sys_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.excluded_table.setItem(i, 0, sys_item)

            name_item = QTableWidgetItem(item.get('display_name', '') or '—')
            self.excluded_table.setItem(i, 1, name_item)

            del_item = QTableWidgetItem('✕')
            del_item.setTextAlignment(Qt.AlignCenter)
            del_item.setForeground(QColor(COLOR_DANGER))
            del_font = del_item.font()
            del_font.setBold(True)
            del_item.setFont(del_font)
            self.excluded_table.setItem(i, 2, del_item)

        self.excluded_table.resizeRowsToContents()
        logger.debug(f'Обновление исключений: {len(excluded)} приложений')

    def _on_excluded_context_menu(self, pos):
        """Контекстное меню для таблицы исключений."""
        row = self.excluded_table.rowAt(pos.y())
        if row < 0:
            return
        system_id = self.excluded_table.item(row, 0).text()

        menu = QMenu(self)
        action_delete = QAction('Удалить', self)
        action_delete.triggered.connect(
            lambda: self._remove_excluded(system_id)
        )
        menu.addAction(action_delete)
        menu.exec_(QCursor.pos())

    def _remove_excluded(self, system_id: str):
        """Убрать приложение из исключений."""
        reply = QMessageBox.question(
            self, 'Удаление исключения',
            f'Убрать "{system_id}" из списка исключений?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.remove_excluded_app(system_id)
            if self._monitor:
                self._monitor._refresh_excluded_cache()
            self._refresh_all()

    def _add_exclude_dialog(self):
        """Диалог добавления исключения."""
        from ui.dialogs.limit_dialog import AddLimitDialog
        dialog = AddLimitDialog(
            self.db, self, title='Добавить исключение',
            label='Введите имя процесса (system_id) для исключения:'
        )
        if dialog.exec_() == QDialog.Accepted and dialog.app_name:
            self.db.add_excluded_app(dialog.app_name, dialog.app_name)
            if self._monitor:
                self._monitor._refresh_excluded_cache()
            self._refresh_all()
            logger.info(f'Добавлено исключение: {dialog.app_name}')

    # ── Общее обновление ────────────────────────────────────────────

    def _refresh_all(self):
        """Обновить все вкладки."""
        self._refresh_open_tab()
        self._refresh_tracked_tab()
        self._refresh_excluded_tab()

    # ── Прочее ──────────────────────────────────────────────────────

    def _open_settings(self):
        logger.info(f'Открытие окна настроек (authorized={self._settings_authorized})')
        try:
            dialog = SettingsDialog(self.db, self, skip_auth=self._settings_authorized)
            dialog.exec_()
            if dialog._authorized:
                self._settings_authorized = True
                logger.info('Авторизация подтверждена, _settings_authorized=True')
            logger.info('Окно настроек закрыто')
            self._refresh_all()
        except Exception as e:
            if str(e) == '_abort_init':
                logger.debug('Настройки не открыты (отмена авторизации)')
            else:
                raise

    def _open_stats(self):
        logger.info('Открытие окна статистики')
        dialog = StatsDialog(self.db, self)
        dialog.exec_()

    def extend_limit(self, app_name: str) -> bool:
        current = self._extensions.get(app_name, 0)
        if current + self.EXTENSION_STEP > self.MAX_EXTENSION_TOTAL:
            logger.warning(f'Превышен лимит продления для {app_name}: {current} + {self.EXTENSION_STEP} > {self.MAX_EXTENSION_TOTAL}')
            return False
        self._extensions[app_name] = current + self.EXTENSION_STEP
        logger.info(f'Лимит продлён для {app_name}: {current} -> {self._extensions[app_name]} мин')
        return True

    def show_limit_notification(self, app_name: str, limit_minutes: int):
        logger.warning(f'Лимит превышен: {app_name} > {limit_minutes} мин')
        if self.tray.notifier:
            self.tray.notifier.show_limit_notification(app_name, limit_minutes)

    def closeEvent(self, event):
        logger.info('Попытка закрытия окна — сворачивание в трей')
        event.ignore()
        self.hide()

    def cleanup(self):
        logger.info('Очистка ресурсов MainWindow')
        self._timer.stop()
        self._active_timer.stop()
        if hasattr(self, 'tray') and self.tray:
            self.tray.hide()
        logger.info('MainWindow очищен')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F4 and event.modifiers() & Qt.AltModifier:
            logger.debug('Alt+F4 заблокирован — сворачивание в трей')
            self.hide()
            return
        super().keyPressEvent(event)
