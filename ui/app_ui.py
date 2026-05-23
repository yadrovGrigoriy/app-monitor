"""
AppUI — локальный интерфейс монитора активности.
Наследует BaseUI и работает напрямую с БД и монитором.
"""

import datetime
from typing import Optional

from PyQt5.QtWidgets import QApplication, QTableWidgetItem
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from ui.base_ui import BaseUI
from ui.tray_manager import TrayManager
from ui.widgets.status_bar import StatusBar
from ui.styles import global_style, tab_table_style, COLOR_DANGER, COLOR_TEXT_SECONDARY
from core.database import Database
from core.auth import AuthManager
from core.role_manager import RoleManager, ROLE_ADMIN, ROLE_USER
from core.logger import setup_logger

logger = setup_logger('ui.app_ui')


class AppUI(BaseUI):
    """Локальный интерфейс монитора активности.

    Работает напрямую с БД и ActivityMonitor.
    Добавляет:
    - Трей-иконку
    - Интеграцию с монитором (активные окна, лимиты)
    - Открытые приложения на вкладке активности
    """

    WARNING_NOTIFY_INTERVAL_MIN = 5
    MAX_EXTENSION_TOTAL = 15
    EXTENSION_STEP = 5

    def __init__(self, db: Database, monitor=None):
        self.db = db
        self._monitor = monitor
        self._auth_manager = AuthManager(db)
        self._role_manager = RoleManager(db)
        self._role_manager.set_role(ROLE_USER)
        self._settings_authorized = True
        self._notified_warning: set[str] = set()
        self._last_exceeded_notify: dict[str, datetime.datetime] = {}
        self._extensions: dict[str, int] = {}

        super().__init__()

        self.status_bar = StatusBar()
        self._init_status_bar()

        self._init_tray()
        self._connect_monitor_signals()
        self._apply_role_restrictions()

    # ── Реализация абстрактных методов ──────────────────────────────

    def get_db(self):
        return self.db

    def get_auth_manager(self):
        return self._auth_manager

    def fetch_activity(self, date_iso: str) -> list:
        return self.db.get_daily_activity(date_iso)

    def fetch_tracked_activity(self, date_iso: str) -> list:
        return self.db.get_tracked_activity(date_iso)

    def fetch_limits(self) -> list:
        return self.db.get_all_limits()

    def fetch_excluded(self) -> list:
        return self.db.get_excluded_apps()

    def fetch_open_windows(self) -> list[dict]:
        """Получить список открытых окон (с активностью)."""
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
        # Группируем по system_id — показываем только одно окно на приложение
        seen_sys = {}
        for w in windows:
            sys_id = w['system_id'].lower()
            if sys_id not in seen_sys:
                seen_sys[sys_id] = w
        return list(seen_sys.values())

    def set_limit(self, system_id: str, limit_minutes: int, enabled: bool, app_name: str = ""):
        self.db.set_limit(system_id, limit_minutes, enabled, app_name=app_name)

    def delete_limit(self, system_id: str):
        self.db.delete_limit_by_system_id(system_id)

    def mark_tracked(self, system_id: str, tracked: bool):
        if tracked:
            self.db.mark_as_tracked(system_id)
        else:
            self.db.mark_as_untracked(system_id)

    def add_excluded(self, system_id: str, display_name: str = ""):
        self.db.add_excluded_app(system_id, display_name)

    def remove_excluded(self, system_id: str):
        self.db.remove_excluded_app(system_id)

    def get_app_by_system_id(self, system_id: str) -> Optional[dict]:
        return self.db.get_app_by_system_id(system_id)

    def get_all_apps(self) -> list:
        return self.db.get_all_apps()

    def get_daily_activity_for_app(self, system_id: str, start_date: str, end_date: str) -> list:
        return self.db.get_daily_activity_for_app_by_system_id(system_id, start_date, end_date)

    def get_activity_for_period(self, start_date: str, end_date: str) -> list:
        return self.db.get_activity_for_period(start_date, end_date)

    def get_tracked_activity_for_period(self, start_date: str, end_date: str) -> list:
        return self.db.get_tracked_activity_for_period(start_date, end_date)

    def get_setting(self, key: str, default: str = "") -> str:
        return self.db.get_setting(key, default)

    def set_setting(self, key: str, value: str):
        self.db.set_setting(key, value)

    def admin_exists(self) -> bool:
        return self.db.admin_exists()

    def verify_local(self, username: str, password: str) -> bool:
        return self._auth_manager.verify_local(username, password)

    def register_admin(self, username: str, password: str) -> bool:
        return self._auth_manager.register(username, password)

    def refresh_excluded_cache(self):
        if self._monitor:
            self._monitor._refresh_excluded_cache()

    # ── Панель состояния ──────────────────────────────────────────

    def _init_status_bar(self):
        """Инициализировать панель состояния."""
        self.status_bar_layout.addWidget(self.status_bar)
        # Статус сервера — по умолчанию запущен
        self.status_bar.set_server_status(True, '0.0.0.0', 8765)
        # Статус мониторинга
        running = self._monitor is not None and self._monitor._running
        self.status_bar.set_monitor_status(running)
        # Локальный IP
        self.status_bar.set_local_ip(self._get_local_ip())
        # Таймер обновления статуса
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._tick_status)
        self._status_timer.start(5000)

    def _get_local_ip(self) -> str:
        """Получить локальный IP-адрес."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            s.connect(('10.254.254.254', 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'

    def _tick_status(self):
        """Обновить статусы на панели."""
        # Мониторинг
        running = self._monitor is not None and self._monitor._running
        apps_count = 0
        if running:
            try:
                apps_count = len(self.fetch_open_windows())
            except Exception:
                pass
        self.status_bar.set_monitor_status(running, apps_count)

    # ── Трей ────────────────────────────────────────────────────────

    def _init_tray(self):
        logger.debug('Инициализация трей-иконки')
        self.tray = TrayManager(self)
        self.tray.show_requested.connect(self.show_and_raise)
        self.tray.settings_requested.connect(self._open_settings)
        logger.debug('Трей-иконка создана')

    # ── Монитор ─────────────────────────────────────────────────────

    def _connect_monitor_signals(self):
        """Подключить сигналы монитора."""
        if self._monitor:
            self._monitor.limit_reached.connect(self._on_limit_reached)

    def _on_limit_reached(self, system_id: str, limit_minutes: int):
        """Обработчик превышения лимита."""
        logger.warning(f'Лимит превышен: {system_id} > {limit_minutes} мин')
        if hasattr(self, 'tray') and self.tray and self.tray.notifier:
            self.tray.notifier.show_limit_notification(system_id, limit_minutes)

    def extend_limit(self, app_name: str) -> bool:
        """Продлить лимит для приложения."""
        current = self._extensions.get(app_name, 0)
        if current + self.EXTENSION_STEP > self.MAX_EXTENSION_TOTAL:
            logger.warning(f'Превышен лимит продления для {app_name}: {current} + {self.EXTENSION_STEP} > {self.MAX_EXTENSION_TOTAL}')
            return False
        self._extensions[app_name] = current + self.EXTENSION_STEP
        logger.info(f'Лимит продлён для {app_name}: {current} -> {self._extensions[app_name]} мин')
        return True

    # ── Обновление ──────────────────────────────────────────────────

    def _refresh_activity_tab(self):
        """Обновить вкладку активности с учётом открытых окон."""
        windows = self.fetch_open_windows()
        today = datetime.date.today().isoformat()
        tracked_apps = self.db.get_tracked_apps()
        tracked_set = {a['system_id'].lower() for a in tracked_apps if a['system_id']}
        limits_by_sys = {}
        for l in self.db.get_all_limits():
            if l.get('system_id'):
                limits_by_sys[l['system_id'].lower()] = l

        conn = self.db._get_connection()
        try:
            activity_rows = conn.execute(
                'SELECT a.system_id, a.app_name, d.total_seconds '
                'FROM daily_activity d '
                'INNER JOIN apps a ON a.id = d.app_id '
                'WHERE d.date = ? AND d.total_seconds > 0',
                (today,)
            ).fetchall()
            activity = {r['system_id'].lower(): dict(r) for r in activity_rows}
        finally:
            conn.close()

        windows_sorted = sorted(
            windows,
            key=lambda w: activity.get(w['system_id'].lower(), {}).get('total_seconds', 0),
            reverse=True
        )

        self.activity_table.setRowCount(len(windows_sorted))
        for i, w in enumerate(windows_sorted):
            sys_id_lower = w['system_id'].lower()
            is_tracked = sys_id_lower in tracked_set
            row_data = activity.get(sys_id_lower, {})
            duration = row_data.get('total_seconds', 0)

            sys_item = QTableWidgetItem(w['system_id'])
            sys_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.activity_table.setItem(i, 0, sys_item)

            app_name = row_data.get('app_name', '') or w['display_name']
            name_item = QTableWidgetItem(app_name)
            name_item.setForeground(QColor('#000000'))
            self.activity_table.setItem(i, 1, name_item)

            hours = duration // 3600
            minutes = (duration % 3600) // 60
            secs = duration % 60
            time_str = f'{hours}:{minutes:02d}:{secs:02d}'
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignCenter)
            time_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.activity_table.setItem(i, 2, time_item)

            limit = limits_by_sys.get(sys_id_lower)
            limit_item = QTableWidgetItem()
            if limit and limit['enabled']:
                exceeded = duration // 60 >= limit['limit_minutes']
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

            if limit and limit['enabled'] and duration // 60 >= limit['limit_minutes']:
                bg_color = QColor('#fde7e9')
            elif is_tracked:
                bg_color = QColor('#e8f5e9')
            else:
                bg_color = QColor('#ffffff')

            for col in range(4):
                item = self.activity_table.item(i, col)
                if item:
                    item.setBackground(bg_color)

        self.activity_table.resizeRowsToContents()
        logger.debug(f'Обновление открытых приложений: {len(windows_sorted)} окон')

    def _tick_activity_tab(self):
        """Обновить время на вкладке активности (с учётом открытых окон)."""
        try:
            current = self.tabs.currentIndex()
            if current != 0:
                return
            today = datetime.date.today().isoformat()
            for row in range(self.activity_table.rowCount()):
                sys_item = self.activity_table.item(row, 0)
                if sys_item:
                    self._update_activity_row_time(row, sys_item.text().lower(), today)
        except Exception as e:
            logger.error(f'Ошибка в _tick_activity_tab: {e}')

    # ── Очистка ─────────────────────────────────────────────────────

    def cleanup(self):
        super().cleanup()
        if hasattr(self, 'tray') and self.tray:
            self.tray.hide()
        logger.info('AppUI очищен')
