"""
Базовый класс UI для AppMonitor.
Содержит общую логику для локального (AppUI) и удалённого (AdminUI) интерфейсов.
"""

import datetime
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QPushButton, QMessageBox, QDialog, QApplication,
)
from PyQt5.QtCore import Qt, QTimer, QDate, pyqtSignal
from PyQt5.QtGui import QColor, QCursor
from PyQt5.QtWidgets import QMenu, QAction

from ui.styles import global_style, tab_table_style, COLOR_DANGER, COLOR_TEXT_SECONDARY

from ui.widgets.bottom_bar import BottomBar
from ui.widgets.tracked_table import TrackedTable
from ui.dialogs.auth_dialogs import AuthDialog, RegisterDialog
from ui.dialogs.limit_dialog import AddLimitDialog, EditLimitDialog
from ui.dialogs.stats_dialog import StatsDialog
from ui.dialogs.settings_dialog import SettingsDialog
from core.auth import AuthManager
from core.role_manager import RoleManager, ROLE_ADMIN, ROLE_USER
from core.logger import setup_logger

logger = setup_logger('ui.base_ui')


class BaseUI(QMainWindow):
    """Базовый класс UI для AppMonitor.

    Предоставляет:
    - Общую структуру вкладок (открытые, отслеживаемые, исключения)
    - Нижнюю панель с кнопками
    - Механизм авторизации и ролей
    - Таймеры обновления
    - Работу с лимитами и исключениями
    """

    UPDATE_INTERVAL_MS = 5000
    ACTIVE_TICK_INTERVAL_MS = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        if not hasattr(self, '_role_manager') or self._role_manager is None:
            self._role_manager: Optional[RoleManager] = None
        self._settings_authorized = True
        self._extensions: dict[str, int] = {}

        self._init_ui()
        self._init_timer()
        self._init_active_timer()

    # ── Абстрактные методы (переопределяются в наследниках) ──────────

    def get_db(self):
        """Вернуть объект базы данных (для AppUI) или None (для AdminUI)."""
        raise NotImplementedError

    def get_auth_manager(self):
        """Вернуть AuthManager (для AppUI) или HTTP-клиент (для AdminUI)."""
        raise NotImplementedError

    def fetch_activity(self, date_iso: str) -> list:
        """Получить активность за дату."""
        raise NotImplementedError

    def fetch_tracked_activity(self, date_iso: str) -> list:
        """Получить отслеживаемые приложения с активностью."""
        raise NotImplementedError

    def fetch_limits(self) -> list:
        """Получить список лимитов."""
        raise NotImplementedError

    def fetch_excluded(self) -> list:
        """Получить список исключений."""
        raise NotImplementedError

    def fetch_open_windows(self) -> list[dict]:
        """Получить список открытых окон (только для AppUI)."""
        return []

    def set_limit(self, system_id: str, limit_minutes: int, enabled: bool, app_name: str = ""):
        """Установить лимит."""
        raise NotImplementedError

    def delete_limit(self, system_id: str):
        """Удалить лимит."""
        raise NotImplementedError

    def mark_tracked(self, system_id: str, tracked: bool):
        """Отметить приложение как отслеживаемое/неотслеживаемое."""
        raise NotImplementedError

    def add_excluded(self, system_id: str, display_name: str = ""):
        """Добавить приложение в исключения."""
        raise NotImplementedError

    def remove_excluded(self, system_id: str):
        """Удалить приложение из исключений."""
        raise NotImplementedError

    def get_app_by_system_id(self, system_id: str) -> Optional[dict]:
        """Получить приложение по system_id."""
        raise NotImplementedError

    def get_all_apps(self) -> list:
        """Получить все приложения."""
        raise NotImplementedError

    def get_daily_activity_for_app(self, system_id: str, start_date: str, end_date: str) -> list:
        """Получить активность приложения за период."""
        raise NotImplementedError

    def get_activity_for_period(self, start_date: str, end_date: str) -> list:
        """Получить активность за период."""
        raise NotImplementedError

    def get_tracked_activity_for_period(self, start_date: str, end_date: str) -> list:
        """Получить активность отслеживаемых за период."""
        raise NotImplementedError

    def get_setting(self, key: str, default: str = "") -> str:
        """Получить настройку."""
        raise NotImplementedError

    def set_setting(self, key: str, value: str):
        """Установить настройку."""
        raise NotImplementedError

    def admin_exists(self) -> bool:
        """Проверить, существует ли администратор."""
        raise NotImplementedError

    def verify_local(self, username: str, password: str) -> bool:
        """Проверить логин/пароль локально."""
        raise NotImplementedError

    def register_admin(self, username: str, password: str) -> bool:
        """Зарегистрировать администратора."""
        raise NotImplementedError

    def refresh_excluded_cache(self):
        """Обновить кеш исключений (для монитора)."""
        pass

    # ── Адаптеры для совместимости с диалогами ──────────────────────
    # Диалоги (AddLimitDialog, EditLimitDialog, SettingsDialog, StatsDialog)
    # ожидают объект с методами Database. Мы подменяем db = self,
    # поэтому предоставляем эти методы как адаптеры.

    def get_today_activity(self) -> list:
        """Адаптер для AddLimitDialog._load_apps."""
        today = datetime.date.today().isoformat()
        return self.fetch_activity(today)

    def get_all_limits(self) -> list:
        """Адаптер для AddLimitDialog._load_apps."""
        return self.fetch_limits()

    def get_excluded_apps(self) -> list:
        """Адаптер для SettingsDialog."""
        return self.fetch_excluded()

    def get_tracked_apps(self) -> list:
        """Адаптер для SettingsDialog."""
        return self.fetch_tracked_activity(datetime.date.today().isoformat())

    def get_daily_activity(self, date_iso: str) -> list:
        """Адаптер для SettingsDialog._refresh_limits_table."""
        return self.fetch_activity(date_iso)

    def get_daily_activity_for_app_by_system_id(self, system_id: str, start_date: str, end_date: str) -> list:
        """Адаптер для StatsDialog."""
        return self.get_daily_activity_for_app(system_id, start_date, end_date)

    def delete_limit_by_system_id(self, system_id: str):
        """Адаптер для SettingsDialog._delete_limit."""
        self.delete_limit(system_id)

    def add_excluded_app(self, system_id: str, display_name: str = ""):
        """Адаптер для SettingsDialog._add_exclude."""
        self.add_excluded(system_id, display_name)

    def remove_excluded_app(self, system_id: str):
        """Адаптер для SettingsDialog._on_exclude_table_click."""
        self.remove_excluded(system_id)

    def close(self):
        """Адаптер для Database.close (заглушка)."""
        pass

    # ── Инициализация UI ────────────────────────────────────────────

    def _init_ui(self):
        logger.debug('Инициализация базового UI')
        self.setWindowTitle('Главная')
        self.setMinimumSize(720, 500)
        self.resize(900, 600)
        self.setStyleSheet(global_style())

        central = QWidget()

        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # Вкладки
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, stretch=1)

        # ── Вкладка 1: Активность ───────────────────────────────────
        self.activity_tab = QWidget()
        activity_layout = QVBoxLayout(self.activity_tab)
        activity_layout.setContentsMargins(0, 4, 0, 4)
        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels(['Имя процесса', 'Приложение', 'Время', 'Лимит'])
        self.activity_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.activity_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.activity_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.activity_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setShowGrid(False)
        self.activity_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.activity_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.activity_table.verticalHeader().setVisible(False)
        self.activity_table.setStyleSheet(tab_table_style())
        self.activity_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.activity_table.customContextMenuRequested.connect(self._on_activity_context_menu)
        self.activity_table.cellDoubleClicked.connect(self._on_activity_double_click)
        activity_layout.addWidget(self.activity_table, stretch=1)
        self.tabs.addTab(self.activity_tab, 'Открытые приложения')

        # ── Вкладка 2: Отслеживаемые ────────────────────────────────
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
        self.excluded_table.setStyleSheet(tab_table_style())
        self.excluded_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.excluded_table.customContextMenuRequested.connect(self._on_excluded_context_menu)
        excluded_layout.addWidget(self.excluded_table, stretch=1)

        btn_row = QHBoxLayout()
        self.btn_add_exclude = QPushButton('Добавить исключение')
        self.btn_add_exclude.clicked.connect(self._add_exclude_dialog)
        btn_row.addWidget(self.btn_add_exclude)
        btn_row.addStretch()
        excluded_layout.addLayout(btn_row)

        self.tabs.addTab(self.excluded_tab, 'Исключения')

        # Нижняя панель
        self.bottom_bar = BottomBar()
        self.bottom_bar.settings_clicked.connect(self._open_settings)
        self.bottom_bar.stats_clicked.connect(self._open_stats)
        self.bottom_bar.refresh_clicked.connect(self._refresh_all)
        self.bottom_bar.auth_clicked.connect(self._open_auth_dialog)
        layout.addWidget(self.bottom_bar)

        # Панель состояния (добавляется наследником)
        self.status_bar_container = QWidget()
        self.status_bar_layout = QVBoxLayout(self.status_bar_container)
        self.status_bar_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.status_bar_container)

        logger.debug('Базовый UI инициализирован')

    def _init_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_all)
        self._timer.start(self.UPDATE_INTERVAL_MS)

    def _init_active_timer(self):
        """Таймер для обновления времени каждую секунду."""
        self._active_timer = QTimer(self)
        self._active_timer.timeout.connect(self._tick_active)
        self._active_timer.start(self.ACTIVE_TICK_INTERVAL_MS)

    # ── Обновление вкладок ──────────────────────────────────────────

    def _tick_active(self):
        """Обновить время на активной вкладке (каждую секунду)."""
        try:
            current = self.tabs.currentIndex()
            if current == 0:
                self._tick_activity_tab()
            elif current == 1:
                self._tick_tracked_tab()
        except Exception as e:
            logger.error(f'Ошибка в _tick_active: {e}')

    def _tick_activity_tab(self):
        """Обновить время на вкладке активности."""
        today = datetime.date.today().isoformat()
        for row in range(self.activity_table.rowCount()):
            sys_item = self.activity_table.item(row, 0)
            if sys_item:
                self._update_activity_row_time(row, sys_item.text().lower(), today)

    def _tick_tracked_tab(self):
        """Обновить время на вкладке отслеживаемых."""
        today = datetime.date.today().isoformat()
        for row in range(self.tracked_table.rowCount()):
            sys_item = self.tracked_table.item(row, 0)
            if sys_item:
                self._update_tracked_row_time(row, sys_item.text().lower(), today)

    def _update_activity_row_time(self, row: int, system_id: str, date_iso: str):
        """Обновить время для строки на вкладке активности."""
        app = self.get_app_by_system_id(system_id)
        if not app:
            duration = 0
        else:
            activity = self.fetch_activity(date_iso)
            match = [a for a in activity if a.get('system_id', '').lower() == system_id]
            duration = match[0].get('total_seconds', 0) if match else 0

        hours = duration // 3600
        minutes = (duration % 3600) // 60
        secs = duration % 60
        time_str = f'{hours}:{minutes:02d}:{secs:02d}'

        limit = self._find_limit(system_id)
        exceeded = limit and limit['enabled'] and duration // 60 >= limit['limit_minutes']

        time_item = self.activity_table.item(row, 2)
        if time_item:
            time_item.setText(time_str)

        if exceeded:
            bg = QColor('#fde7e9')
        else:
            bg = QColor('#ffffff')

        for col in range(4):
            cell = self.activity_table.item(row, col)
            if cell:
                cell.setBackground(bg)

    def _update_tracked_row_time(self, row: int, system_id: str, date_iso: str):
        """Обновить время для строки на вкладке отслеживаемых."""
        app = self.get_app_by_system_id(system_id)
        if not app:
            duration = 0
        else:
            activity = self.fetch_tracked_activity(date_iso)
            match = [a for a in activity if a.get('system_id', '').lower() == system_id]
            duration = match[0].get('total_seconds', 0) if match else 0

        hours = duration // 3600
        minutes = (duration % 3600) // 60
        secs = duration % 60
        time_str = f'{hours}:{minutes:02d}:{secs:02d}'

        time_item = self.tracked_table.item(row, 2)
        if time_item:
            time_item.setText(time_str)

        limit = self._find_limit(system_id)
        if limit and limit['enabled'] and duration // 60 >= limit['limit_minutes']:
            row_bg = QColor('#fde7e9')
        else:
            row_bg = QColor('#ffffff')

        limit_item = self.tracked_table.item(row, 3)
        if limit_item and limit and limit['enabled']:
            exceeded = duration // 60 >= limit['limit_minutes']
            limit_str = f'{limit["limit_minutes"]} мин'
            if exceeded:
                limit_str += ' ⚠'
                limit_item.setForeground(QColor(COLOR_DANGER))
            else:
                limit_item.setForeground(QColor('#107c10'))
            limit_item.setText(limit_str)
        limit_item.setBackground(row_bg)

        remaining_item = self.tracked_table.item(row, 4)
        if remaining_item and limit and limit['enabled']:
            used = duration // 60
            left = max(0, limit['limit_minutes'] - used)
            remaining_item.setText(f'{left} мин')
            if left == 0:
                remaining_item.setForeground(QColor(COLOR_DANGER))
            else:
                remaining_item.setForeground(QColor('#107c10'))
        remaining_item.setBackground(row_bg)

        for col in range(2):
            cell = self.tracked_table.item(row, col)
            if cell:
                cell.setBackground(row_bg)

    def _find_limit(self, system_id: str) -> Optional[dict]:
        """Найти лимит по system_id."""
        limits = self.fetch_limits()
        for l in limits:
            if l.get('system_id', '').lower() == system_id.lower():
                return l
        return None

    def _refresh_activity_tab(self):
        """Обновить вкладку активности."""
        today = datetime.date.today().isoformat()
        activity = self.fetch_activity(today)
        limits = {l.get('system_id', '').lower(): l for l in self.fetch_limits()}

        self.activity_table.setRowCount(len(activity))
        for i, item in enumerate(activity):
            sys_id = item.get('system_id', '').lower()
            sys_item = QTableWidgetItem(item.get('system_id', ''))
            sys_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.activity_table.setItem(i, 0, sys_item)

            name_item = QTableWidgetItem(item['app_name'])
            name_item.setForeground(QColor('#000000'))
            self.activity_table.setItem(i, 1, name_item)

            hours = item['total_seconds'] // 3600
            minutes = (item['total_seconds'] % 3600) // 60
            secs = item['total_seconds'] % 60
            time_str = f'{hours}:{minutes:02d}:{secs:02d}'
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignCenter)
            time_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.activity_table.setItem(i, 2, time_item)

            limit = limits.get(sys_id)
            limit_item = QTableWidgetItem()
            if limit and limit['enabled']:
                exceeded = item['total_seconds'] // 60 >= limit['limit_minutes']
                limit_str = f'{limit["limit_minutes"]} мин'
                if exceeded:
                    limit_str += ' ⚠'
                    limit_item.setForeground(QColor(COLOR_DANGER))
                else:
                    limit_item.setForeground(QColor('#107c10'))
            else:
                limit_str = '—'
                limit_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            limit_item.setText(limit_str)
            limit_item.setTextAlignment(Qt.AlignCenter)
            self.activity_table.setItem(i, 3, limit_item)

            # Цвет фона строки
            if limit and limit['enabled'] and item['total_seconds'] // 60 >= limit['limit_minutes']:
                bg = QColor('#fde7e9')
            else:
                bg = QColor('#ffffff')
            for col in range(4):
                cell = self.activity_table.item(i, col)
                if cell:
                    cell.setBackground(bg)

        self.activity_table.resizeRowsToContents()
        logger.debug(f'Обновление активности: {len(activity)} записей')

    def _refresh_tracked_tab(self):
        """Обновить вкладку отслеживаемых."""
        today = datetime.date.today().isoformat()
        items = self.fetch_tracked_activity(today)
        limits = {l.get('system_id', '').lower(): l for l in self.fetch_limits()}
        self.tracked_table.populate(items, limits)
        logger.debug(f'Обновление отслеживаемых: {len(items)} приложений')

    def _refresh_excluded_tab(self):
        """Обновить вкладку исключений."""
        excluded = self.fetch_excluded()
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

    def _refresh_all(self):
        """Обновить все вкладки."""
        try:
            self._refresh_activity_tab()
        except Exception as e:
            logger.error(f'Ошибка обновления активности: {e}', exc_info=True)
        try:
            self._refresh_tracked_tab()
        except Exception as e:
            logger.error(f'Ошибка обновления отслеживаемых: {e}', exc_info=True)
        try:
            self._refresh_excluded_tab()
        except Exception as e:
            logger.error(f'Ошибка обновления исключений: {e}', exc_info=True)

    # ── Обработчики вкладок ─────────────────────────────────────────

    def _on_activity_context_menu(self, pos):
        """Контекстное меню для таблицы активности."""
        if not self._is_admin():
            return
        row = self.activity_table.rowAt(pos.y())
        if row < 0:
            return
        sys_id = self.activity_table.item(row, 0).text()
        app_name = self.activity_table.item(row, 1).text()

        app = self.get_app_by_system_id(sys_id)
        is_tracked = app and app.get('is_tracked', False)

        menu = QMenu(self)
        if not is_tracked:
            action_track = QAction('Добавить для отслеживания', self)
            action_track.triggered.connect(lambda: self._add_track(sys_id, app_name))
            menu.addAction(action_track)

        action_exclude = QAction('Исключить', self)
        action_exclude.triggered.connect(lambda: self._exclude_app(sys_id, app_name))
        menu.addAction(action_exclude)

        menu.exec_(QCursor.pos())

    def _on_activity_double_click(self, row: int, column: int):
        """По двойному клику — перейти на вкладку отслеживаемых."""
        if not self._is_admin():
            return
        sys_id_item = self.activity_table.item(row, 0)
        if not sys_id_item:
            return
        sys_id = sys_id_item.text()
        app = self.get_app_by_system_id(sys_id)
        if not app:
            return
        app_name = app['app_name']
        self.tabs.setCurrentIndex(1)
        for r in range(self.tracked_table.rowCount()):
            item = self.tracked_table.item(r, 1)
            if item and item.text() == app_name:
                self.tracked_table.selectRow(r)
                self.tracked_table.scrollToItem(item)
                break

    def _add_track(self, system_id: str, display_name: str):
        """Добавить приложение для отслеживания."""
        logger.info(f'Добавление для отслеживания: {system_id} ({display_name})')
        self.mark_tracked(system_id, True)
        self._refresh_all()

    def _exclude_app(self, system_id: str, display_name: str):
        """Исключить приложение."""
        logger.info(f'Исключение приложения: {system_id} ({display_name})')
        self.add_excluded(system_id, display_name)
        self.refresh_excluded_cache()
        self._refresh_all()

    def _add_limit_from_tracked(self, app_name: str):
        """Добавить лимит для отслеживаемого приложения."""
        logger.info(f'Добавление лимита из отслеживаемых: {app_name}')
        dialog = AddLimitDialog(None, self, preset_app=app_name)
        # Подменяем db на наш адаптер
        dialog.db = self
        if dialog.exec_() == QDialog.Accepted and dialog.app_name:
            app = self.get_app_by_system_id(app_name.lower())
            if not app:
                all_apps = self.get_all_apps()
                for a in all_apps:
                    if a['app_name'].lower() == app_name.lower():
                        app = a
                        break
            system_id = app['system_id'] if app else app_name.lower()
            self.set_limit(system_id, dialog.limit_minutes, True, app_name=dialog.app_name)
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
            self.mark_tracked(system_id, False)
            self._refresh_all()

    def _on_excluded_context_menu(self, pos):
        """Контекстное меню для таблицы исключений."""
        if not self._is_admin():
            return
        row = self.excluded_table.rowAt(pos.y())
        if row < 0:
            return
        system_id = self.excluded_table.item(row, 0).text()

        menu = QMenu(self)
        action_delete = QAction('Удалить', self)
        action_delete.triggered.connect(lambda: self._remove_excluded(system_id))
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
            self.remove_excluded(system_id)
            self.refresh_excluded_cache()
            self._refresh_all()

    def _add_exclude_dialog(self):
        """Диалог добавления исключения."""
        dialog = AddLimitDialog(
            None, self, title='Добавить исключение',
            label='Введите имя процесса (system_id) для исключения:'
        )
        dialog.db = self
        if dialog.exec_() == QDialog.Accepted and dialog.app_name:
            self.add_excluded(dialog.app_name, dialog.app_name)
            self.refresh_excluded_cache()
            self._refresh_all()
            logger.info(f'Добавлено исключение: {dialog.app_name}')

    # ── Настройки и статистика ──────────────────────────────────────

    def _open_settings(self):
        """Открыть окно настроек."""
        logger.info('Открытие окна настроек')
        try:
            dialog = SettingsDialog(None, self, skip_auth=self._settings_authorized)
            dialog.db = self
            if dialog.exec_() == QDialog.Accepted:
                self._refresh_all()
        except Exception as e:
            if str(e) == '_abort_init':
                logger.debug('Настройки не открыты (отмена авторизации)')
            else:
                raise

    def _open_stats(self):
        """Открыть окно статистики."""
        logger.info('Открытие окна статистики')
        try:
            db = getattr(self, 'db', None)
            if db is None:
                logger.error('Нет доступа к базе данных для статистики')
                return
            dialog = StatsDialog(db, self)
            dialog.exec_()
        except Exception as e:
            logger.error(f'Ошибка при открытии статистики: {e}', exc_info=True)

    # ── Авторизация ─────────────────────────────────────────────────

    def _is_admin(self) -> bool:
        """Проверить, является ли текущий пользователь администратором."""
        return self._role_manager is not None and self._role_manager.is_admin()

    def _open_auth_dialog(self):
        """Обработчик кнопки авторизации/выхода."""
        if self._is_admin():
            self._role_manager.set_role(ROLE_USER)
            self._apply_role_restrictions()
            self._refresh_all()
            logger.info('Выход из режима администратора')
            return

        self._show_login_dialog()

    def _show_login_dialog(self):
        """Показать диалог авторизации."""
        if not self.admin_exists():
            reply = QMessageBox.question(
                self, "Первый вход",
                "Администратор не настроен. Создать учётную запись?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            reg_dialog = RegisterDialog(self)
            if reg_dialog.exec_() != QDialog.Accepted:
                return

            username = reg_dialog.username_input.text()
            password = reg_dialog.password_input.text()
            if self.register_admin(username, password):
                logger.info(f'Создан администратор: {username}')
                self._role_manager.set_role(ROLE_ADMIN)
                self._apply_role_restrictions()
                self._refresh_all()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось создать администратора")
            return

        for attempt in range(3):
            dialog = AuthDialog(self, attempt)
            if dialog.exec_() != QDialog.Accepted:
                return

            username = dialog.username_input.text()
            password = dialog.password_input.text()
            if self.verify_local(username, password):
                logger.info(f'Локальная авторизация: {username}')
                try:
                    self._role_manager.set_role(ROLE_ADMIN)
                    logger.info('Роль установлена, применяем ограничения...')
                    self._apply_role_restrictions()
                    logger.info('Ограничения применены, обновляем UI...')
                    self._refresh_all()
                    logger.info('UI обновлён, авторизация завершена')
                except Exception as e:
                    logger.error(f'Ошибка после авторизации: {e}', exc_info=True)
                return

            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")

        logger.warning('3 неудачных попытки входа')

    def _apply_role_restrictions(self):
        """Применить ограничения в зависимости от текущей роли."""
        is_admin = self._is_admin()

        self.bottom_bar.set_auth_state(is_admin)

        if is_admin:
            self._show_excluded_tab(True)
            self.bottom_bar.btn_settings.setVisible(True)
            self.bottom_bar.btn_stats.setVisible(True)
            self.activity_table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tracked_table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.excluded_table.setContextMenuPolicy(Qt.CustomContextMenu)
            try:
                self.tracked_table.cellDoubleClicked.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                self.tracked_table.cellDoubleClicked.connect(
                    self.tracked_table._on_double_click
                )
            except RuntimeError:
                logger.warning('Не удалось подключить cellDoubleClicked')
                pass
            logger.debug('Роль Admin: полный доступ')
        else:
            self._show_excluded_tab(False)
            self.bottom_bar.btn_settings.setVisible(False)
            self.bottom_bar.btn_stats.setVisible(False)
            self.activity_table.setContextMenuPolicy(Qt.NoContextMenu)
            self.tracked_table.setContextMenuPolicy(Qt.NoContextMenu)
            self.excluded_table.setContextMenuPolicy(Qt.NoContextMenu)
            try:
                self.tracked_table.cellDoubleClicked.disconnect()
            except TypeError:
                pass
            logger.debug('Роль User: только просмотр')

    def _show_excluded_tab(self, visible: bool):
        """Показать или скрыть вкладку исключений."""
        idx = self.tabs.indexOf(self.excluded_tab)
        if idx >= 0:
            self.tabs.setTabVisible(idx, visible)
        if hasattr(self, 'btn_add_exclude'):
            self.btn_add_exclude.setVisible(visible)

    # ── Прочее ──────────────────────────────────────────────────────

    def show_and_raise(self):
        """Показать окно и поднять на передний план."""
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """Закрытие окна — сворачивание в трей (для AppUI)."""
        event.ignore()
        self.hide()

    def refresh_styles(self):
        """Обновить стили при смене темы."""
        self.setStyleSheet(global_style())
        self.activity_table.setStyleSheet(tab_table_style())
        self.excluded_table.setStyleSheet(tab_table_style())
        logger.debug('Стили обновлены')

    def cleanup(self):
        """Очистка ресурсов."""
        self._timer.stop()
        self._active_timer.stop()
        logger.info('Ресурсы очищены')

    def closeEvent(self, event):
        """При закрытии окна сворачиваем в трей."""
        logger.debug('Закрытие окна — сворачивание в трей')
        self.hide()
        event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F4 and event.modifiers() & Qt.AltModifier:
            logger.debug('Alt+F4 — сворачивание в трей')
            self.hide()
            return
        super().keyPressEvent(event)
