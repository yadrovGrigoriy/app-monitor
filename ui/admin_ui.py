"""
AdminUI — удалённый интерфейс администрирования.
Наследует BaseUI и работает через HTTP API.
"""

import datetime
import json
import asyncio
from typing import Optional

import httpx

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QCheckBox,
)
from PyQt5.QtCore import Qt, QTimer, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QColor

from ui.base_ui import BaseUI
from ui.styles import global_style, COLOR_DANGER, COLOR_TEXT_SECONDARY
from core.role_manager import RoleManager, ROLE_ADMIN, ROLE_USER
from core.logger import setup_logger

logger = setup_logger('ui.admin_ui')


class AdminClient:
    """HTTP-клиент для общения с сервером монитора."""

    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url.rstrip("/")
        self.ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        self._token: str | None = None

    def _headers(self) -> dict:
        h = {}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _get(self, path: str):
        r = httpx.get(f"{self.base_url}{path}", headers=self._headers(), timeout=5)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict):
        r = httpx.post(f"{self.base_url}{path}", json=data, headers=self._headers(), timeout=5)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str):
        r = httpx.delete(f"{self.base_url}{path}", headers=self._headers(), timeout=5)
        r.raise_for_status()
        return r.json()

    def login(self, username: str, password: str) -> bool:
        try:
            resp = self._post("/api/auth/login", {"username": username, "password": password})
            self._token = resp["token"]
            logger.info(f'Авторизован как {username}')
            return True
        except Exception as e:
            logger.warning(f'Ошибка авторизации: {e}')
            return False

    def get_status(self) -> dict:
        return self._get("/api/status")

    def get_today_activity(self) -> list:
        return self._get("/api/activity/today")

    def get_activity_by_date(self, date: str) -> list:
        return self._get(f"/api/activity/date/{date}")

    def get_limits(self) -> list:
        return self._get("/api/limits")

    def set_limit(self, system_id: str, limit_minutes: int, enabled: bool = True, app_name: str = ""):
        return self._post("/api/limits", {
            "app_name": app_name or system_id,
            "system_id": system_id,
            "limit_minutes": limit_minutes,
            "enabled": enabled,
        })

    def delete_limit(self, system_id: str):
        return self._delete(f"/api/limits/{system_id}")

    def get_setting(self, key: str, default: str = "") -> str:
        try:
            resp = self._get(f"/api/settings/{key}?default={default}")
            if isinstance(resp, dict):
                return resp.get("value", default)
            return str(resp)
        except Exception:
            return default

    def set_setting(self, key: str, value: str):
        return self._post("/api/settings", {"key": key, "value": value})

    def get_all_settings(self) -> list:
        return self._get("/api/settings")

    def get_apps(self) -> list:
        return self._get("/api/apps")

    def get_tracked_apps(self) -> list:
        return self._get("/api/apps/tracked")

    def set_tracked(self, system_id: str, tracked: bool):
        return self._post("/api/apps/tracked", {"system_id": system_id, "tracked": tracked})

    def get_excluded(self) -> list:
        return self._get("/api/excluded")

    def add_excluded(self, system_id: str):
        return self._post("/api/excluded", {"system_id": system_id, "tracked": False})

    def remove_excluded(self, system_id: str):
        return self._delete(f"/api/excluded/{system_id}")

    def get_activity_period(self, start_date: str, end_date: str) -> dict:
        return self._post("/api/activity/period", {"start_date": start_date, "end_date": end_date})

    def get_tracked_activity_period(self, start_date: str, end_date: str) -> dict:
        return self._post("/api/activity/tracked/period", {"start_date": start_date, "end_date": end_date})

    def get_app_activity(self, system_id: str, start_date: str, end_date: str) -> list:
        return self._get(f"/api/activity/app/{system_id}?start_date={start_date}&end_date={end_date}")


class _AdminLoginDialog(QDialog):
    """Диалог входа для удалённого администрирования."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Вход в монитор")
        self.setMinimumWidth(350)
        layout = QFormLayout(self)
        layout.addRow(QLabel("Авторизация администратора:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("admin")
        layout.addRow("Логин:", self.username_input)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("пароль")
        layout.addRow("Пароль:", self.password_input)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Войти")
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)


class AdminUI(BaseUI):
    """Удалённый интерфейс администрирования.

    Подключается к серверу AppMonitor по HTTP/WebSocket.
    Добавляет:
    - Панель подключения к серверу
    - Выбор даты для просмотра активности
    - WebSocket для real-time обновлений
    """

    def __init__(self):
        self.api: AdminClient | None = None
        self._ws_worker = None
        self._role_manager = RoleManager(None)  # заглушка, роль всегда admin
        self._role_manager.set_role(ROLE_ADMIN)
        self._settings_authorized = True
        self._extensions: dict[str, int] = {}
        self._cached_limits: list = []
        self._cached_excluded: list = []
        self._cached_apps: list = []
        self._current_date: str = datetime.date.today().isoformat()

        super().__init__()

        self._add_connection_panel()
        self._add_date_picker()
        self._apply_role_restrictions()

    # ── Панель подключения ──────────────────────────────────────────

    def _add_connection_panel(self):
        """Добавить панель подключения к серверу."""
        central = self.centralWidget()
        layout = central.layout()

        # Вставляем панель подключения первой
        conn_widget = QWidget()
        conn_layout = QHBoxLayout(conn_widget)
        conn_layout.setContentsMargins(0, 0, 0, 8)

        conn_layout.addWidget(QLabel("Сервер:"))
        self.server_input = QLineEdit("192.168.1.100:8765")
        self.server_input.setPlaceholderText("IP:порт (например, 192.168.1.100:8765)")
        conn_layout.addWidget(self.server_input)

        btn_connect = QPushButton("Подключиться")
        btn_connect.clicked.connect(self._connect)
        conn_layout.addWidget(btn_connect)

        self.conn_status = QLabel("Не подключён")
        self.conn_status.setStyleSheet(f"color: {COLOR_DANGER};")
        conn_layout.addWidget(self.conn_status)

        conn_layout.addStretch()

        # Вставляем в начало layout
        layout.insertWidget(0, conn_widget)

    def _add_date_picker(self):
        """Добавить панель выбора даты."""
        central = self.centralWidget()
        layout = central.layout()

        date_widget = QWidget()
        date_layout = QHBoxLayout(date_widget)
        date_layout.setContentsMargins(0, 0, 0, 4)

        date_layout.addWidget(QLabel("Дата:"))
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.dateChanged.connect(self._on_date_changed)
        date_layout.addWidget(self.date_picker)

        btn_today = QPushButton("Сегодня")
        btn_today.clicked.connect(lambda: self.date_picker.setDate(QDate.currentDate()))
        date_layout.addWidget(btn_today)

        date_layout.addStretch()

        # Вставляем после панели подключения
        layout.insertWidget(1, date_widget)

    def _on_date_changed(self, qdate: QDate):
        """Обработчик смены даты."""
        self._current_date = qdate.toString(Qt.ISODate)
        self._refresh_all()

    # ── Подключение ─────────────────────────────────────────────────

    def _connect(self):
        """Подключиться к серверу."""
        address = self.server_input.text().strip()
        if not address:
            QMessageBox.warning(self, "Ошибка", "Введите адрес сервера")
            return
        if "://" not in address:
            address = f"http://{address}"
        self.api = AdminClient(address)
        try:
            status = self.api.get_status()
            self.conn_status.setText(
                f"Подключён (аптайм: {status['uptime_seconds']}с, приложений: {status['monitored_apps']})"
            )
            self.conn_status.setStyleSheet("color: green;")
            # Авторизация
            if not self._login():
                self.api = None
                self.conn_status.setText("Ошибка авторизации")
                self.conn_status.setStyleSheet(f"color: {COLOR_DANGER};")
                return
            self._refresh_all()
            self._connect_ws()
        except Exception as e:
            self.conn_status.setText(f"Ошибка: {e}")
            self.conn_status.setStyleSheet(f"color: {COLOR_DANGER};")
            self.api = None

    def _login(self) -> bool:
        """Запросить логин/пароль."""
        dialog = _AdminLoginDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return False
        return self.api.login(dialog.username_input.text(), dialog.password_input.text())

    def _connect_ws(self):
        """Подключение к WebSocket."""
        try:
            class WsWorker(QThread):
                message_received = pyqtSignal(str)
                disconnected = pyqtSignal()

                def __init__(self, url):
                    super().__init__()
                    self.url = url
                    self._running = True

                def run(self):
                    import websockets
                    async def _listen():
                        try:
                            async with websockets.connect(self.url) as ws:
                                self.message_received.emit('{"type":"connected"}')
                                while self._running:
                                    try:
                                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                                        self.message_received.emit(msg)
                                    except asyncio.TimeoutError:
                                        await ws.send(json.dumps({"action": "ping"}))
                        except Exception as e:
                            self.message_received.emit(json.dumps({"type": "error", "message": str(e)}))
                        finally:
                            self.disconnected.emit()

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_listen())

                def stop(self):
                    self._running = False

            ws_url = f"{self.api.ws_url}/ws"
            self._ws_worker = WsWorker(ws_url)
            self._ws_worker.message_received.connect(self._on_ws_message)
            self._ws_worker.disconnected.connect(self._on_ws_disconnected)
            self._ws_worker.start()
        except ImportError:
            logger.debug("websockets не установлен, real-time обновления недоступны")

    def _on_ws_message(self, raw: str):
        """Обработка сообщения от WebSocket."""
        try:
            msg = json.loads(raw)
            msg_type = msg.get("type")
            if msg_type == "activity":
                self._refresh_all()
            elif msg_type == "connected":
                logger.debug("WebSocket подключён")
        except json.JSONDecodeError:
            pass

    def _on_ws_disconnected(self):
        logger.debug("WebSocket отключён")

    # ── Реализация абстрактных методов ──────────────────────────────

    def get_db(self):
        return None

    def get_auth_manager(self):
        return self.api

    def fetch_activity(self, date_iso: str) -> list:
        if not self.api:
            return []
        try:
            today = datetime.date.today().isoformat()
            if date_iso == today:
                return self.api.get_today_activity()
            return self.api.get_activity_by_date(date_iso)
        except Exception as e:
            logger.warning(f'Ошибка получения активности: {e}')
            return []

    def fetch_tracked_activity(self, date_iso: str) -> list:
        if not self.api:
            return []
        try:
            # Используем API активности за период (один день)
            resp = self.api.get_tracked_activity_period(date_iso, date_iso)
            return resp.get("apps", [])
        except Exception as e:
            logger.warning(f'Ошибка получения отслеживаемых: {e}')
            return []

    def fetch_limits(self) -> list:
        if not self.api:
            return self._cached_limits
        try:
            self._cached_limits = self.api.get_limits()
        except Exception:
            pass
        return self._cached_limits

    def fetch_excluded(self) -> list:
        if not self.api:
            return self._cached_excluded
        try:
            self._cached_excluded = self.api.get_excluded()
        except Exception:
            pass
        return self._cached_excluded

    def fetch_open_windows(self) -> list[dict]:
        return []

    def set_limit(self, system_id: str, limit_minutes: int, enabled: bool, app_name: str = ""):
        if not self.api:
            return
        try:
            self.api.set_limit(system_id, limit_minutes, enabled, app_name=app_name)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось установить лимит: {e}")

    def delete_limit(self, system_id: str):
        if not self.api:
            return
        try:
            self.api.delete_limit(system_id)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить лимит: {e}")

    def mark_tracked(self, system_id: str, tracked: bool):
        if not self.api:
            return
        try:
            self.api.set_tracked(system_id, tracked)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось изменить статус: {e}")

    def add_excluded(self, system_id: str, display_name: str = ""):
        if not self.api:
            return
        try:
            self.api.add_excluded(system_id)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось добавить исключение: {e}")

    def remove_excluded(self, system_id: str):
        if not self.api:
            return
        try:
            self.api.remove_excluded(system_id)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить исключение: {e}")

    def get_app_by_system_id(self, system_id: str) -> Optional[dict]:
        if not self.api:
            return None
        try:
            apps = self.api.get_apps()
            for a in apps:
                if a.get('system_id', '').lower() == system_id.lower():
                    return a
        except Exception:
            pass
        return None

    def get_all_apps(self) -> list:
        if not self.api:
            return self._cached_apps
        try:
            self._cached_apps = self.api.get_apps()
        except Exception:
            pass
        return self._cached_apps

    def get_daily_activity_for_app(self, system_id: str, start_date: str, end_date: str) -> list:
        if not self.api:
            return []
        try:
            return self.api.get_app_activity(system_id, start_date, end_date)
        except Exception:
            return []

    def get_activity_for_period(self, start_date: str, end_date: str) -> list:
        if not self.api:
            return []
        try:
            resp = self.api.get_activity_period(start_date, end_date)
            return resp.get("apps", [])
        except Exception:
            return []

    def get_tracked_activity_for_period(self, start_date: str, end_date: str) -> list:
        if not self.api:
            return []
        try:
            resp = self.api.get_tracked_activity_period(start_date, end_date)
            return resp.get("apps", [])
        except Exception:
            return []

    def get_setting(self, key: str, default: str = "") -> str:
        if not self.api:
            return default
        try:
            return self.api.get_setting(key, default)
        except Exception:
            return default

    def set_setting(self, key: str, value: str):
        if not self.api:
            return
        try:
            self.api.set_setting(key, value)
        except Exception as e:
            logger.warning(f'Ошибка сохранения настройки {key}: {e}')

    def admin_exists(self) -> bool:
        return True  # Для удалённого доступа админ всегда существует

    def verify_local(self, username: str, password: str) -> bool:
        if not self.api:
            return False
        return self.api.login(username, password)

    def register_admin(self, username: str, password: str) -> bool:
        if not self.api:
            return False
        try:
            resp = self.api._post("/api/auth/register", {"username": username, "password": password})
            return bool(resp.get("token"))
        except Exception:
            return False

    def refresh_excluded_cache(self):
        pass

    # ── Обновление ──────────────────────────────────────────────────

    def _refresh_activity_tab(self):
        """Обновить вкладку активности (через API)."""
        if not self.api:
            return
        try:
            is_today = (self._current_date == datetime.date.today().isoformat())
            if is_today:
                activity = self.api.get_today_activity()
            else:
                activity = self.api.get_activity_by_date(self._current_date)
        except Exception:
            return

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

            # В колонку 2 (Окно) ставим прочерк — через API нет данных об окнах
            title_item = QTableWidgetItem('—')
            title_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.activity_table.setItem(i, 2, title_item)

            hours = item['duration_seconds'] // 3600
            minutes = (item['duration_seconds'] % 3600) // 60
            secs = item['duration_seconds'] % 60
            time_str = f'{hours}:{minutes:02d}:{secs:02d}'
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignCenter)
            time_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.activity_table.setItem(i, 3, time_item)

            limit = limits.get(sys_id)
            if limit and limit['enabled'] and item['duration_seconds'] // 60 >= limit['limit_minutes']:
                bg = QColor('#fde7e9')
            else:
                bg = QColor('#ffffff')

            for col in range(4):
                cell = self.activity_table.item(i, col)
                if cell:
                    cell.setBackground(bg)

        self.activity_table.resizeRowsToContents()
        logger.debug(f'Обновление активности (AdminUI): {len(activity)} записей')

    def _tick_activity_tab(self):
        """Обновить время на вкладке активности (через API)."""
        if not self.api:
            return
        try:
            current = self.tabs.currentIndex()
            if current != 0:
                return
            is_today = (self._current_date == datetime.date.today().isoformat())
            if not is_today:
                return  # Обновляем только для сегодняшней даты
            super()._tick_activity_tab()
        except Exception as e:
            logger.error(f'Ошибка в _tick_activity_tab (AdminUI): {e}')

    # ── Настройки ───────────────────────────────────────────────────

    def _open_settings(self):
        """Открыть окно настроек (через API)."""
        if not self.api:
            QMessageBox.warning(self, "Ошибка", "Сначала подключитесь к серверу")
            return
        from ui.admin_ui import AdminSettingsDialog
        dialog = AdminSettingsDialog(self.api, self)
        dialog.exec_()
        self._refresh_all()

    # ── Очистка ─────────────────────────────────────────────────────

    def cleanup(self):
        super().cleanup()
        if self._ws_worker:
            self._ws_worker.stop()
            self._ws_worker.wait(2000)
        logger.info('AdminUI очищен')


# ─── Диалог настроек для AdminUI ─────────────────────────────────────

class AdminSettingsDialog(QDialog):
    """Диалог настроек для удалённого администрирования."""

    def __init__(self, api: AdminClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Настройки — админ")
        self.setMinimumSize(500, 400)
        self._init_ui()
        self._load()

    def _init_ui(self):
        from PyQt5.QtWidgets import (
            QTabWidget, QSpinBox, QCheckBox, QGroupBox, QFormLayout,
            QDialogButtonBox,
        )
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Вкладка лимитов
        limits_tab = QWidget()
        limits_layout = QVBoxLayout(limits_tab)
        tabs.addTab(limits_tab, "Лимиты")
        limits_layout.addWidget(QLabel("Лимиты времени для приложений:"))
        self.limits_table = QTableWidget()
        self.limits_table.setColumnCount(4)
        self.limits_table.setHorizontalHeaderLabels(["Приложение", "Лимит (мин)", "Включено", ""])
        self.limits_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.limits_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        limits_layout.addWidget(self.limits_table)
        btn_add = QPushButton("Добавить лимит")
        btn_add.clicked.connect(self._add_limit)
        limits_layout.addWidget(btn_add)

        # Вкладка настроек
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        tabs.addTab(settings_tab, "Настройки")
        form_group = QGroupBox("Параметры")
        form = QFormLayout(form_group)
        self.email_from = QLineEdit()
        form.addRow("Email от:", self.email_from)
        self.email_to = QLineEdit()
        form.addRow("Email кому:", self.email_to)
        self.smtp_server = QLineEdit()
        form.addRow("SMTP сервер:", self.smtp_server)
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        form.addRow("SMTP порт:", self.smtp_port)
        self.report_enabled = QCheckBox("Отправлять отчёт")
        form.addRow(self.report_enabled)
        settings_layout.addWidget(form_group)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _load(self):
        try:
            limits = self.api.get_limits()
            self.limits_table.setRowCount(len(limits))
            for i, limit in enumerate(limits):
                self.limits_table.setItem(i, 0, QTableWidgetItem(limit.get("app_name", limit.get("system_id", ""))))
                spin = QSpinBox()
                spin.setRange(1, 1440)
                spin.setValue(limit["limit_minutes"])
                self.limits_table.setCellWidget(i, 1, spin)
                check = QCheckBox()
                check.setChecked(bool(limit["enabled"]))
                self.limits_table.setCellWidget(i, 2, check)
                btn_del = QPushButton("Удалить")
                app_name = limit.get("app_name", limit.get("system_id", ""))
                btn_del.clicked.connect(lambda checked, name=app_name: self._delete_limit(name))
                self.limits_table.setCellWidget(i, 3, btn_del)

            self.email_from.setText(self.api.get_setting("email_from"))
            self.email_to.setText(self.api.get_setting("email_to"))
            self.smtp_server.setText(self.api.get_setting("smtp_server", "smtp.gmail.com"))
            self.smtp_port.setValue(int(self.api.get_setting("smtp_port", "587")))
            self.report_enabled.setChecked(self.api.get_setting("report_enabled", "0") == "1")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить настройки: {e}")

    def _add_limit(self):
        from PyQt5.QtWidgets import QInputDialog
        app_name, ok = QInputDialog.getText(self, "Новый лимит", "Имя приложения (например, chrome.exe):")
        if ok and app_name:
            try:
                self.api.set_limit(app_name.strip(), 60, True, app_name=app_name.strip())
                self._load()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _delete_limit(self, app_name: str):
        try:
            self.api.delete_limit(app_name)
            self._load()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def _save(self):
        try:
            self.api.set_setting("email_from", self.email_from.text())
            self.api.set_setting("email_to", self.email_to.text())
            self.api.set_setting("smtp_server", self.smtp_server.text())
            self.api.set_setting("smtp_port", str(self.smtp_port.value()))
            self.api.set_setting("report_enabled", "1" if self.report_enabled.isChecked() else "0")

            for i in range(self.limits_table.rowCount()):
                app_name = self.limits_table.item(i, 0).text()
                spin = self.limits_table.cellWidget(i, 1)
                check = self.limits_table.cellWidget(i, 2)
                if spin and check:
                    self.api.set_limit(app_name, spin.value(), check.isChecked(), app_name=app_name)

            QMessageBox.information(self, "Готово", "Настройки сохранены")
            self.close()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))
