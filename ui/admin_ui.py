"""
AdminUI — удалённый интерфейс администрирования.
Наследует BaseUI и работает через HTTP API.
"""

import datetime
import json
import asyncio
import os
from typing import Optional

import httpx

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QCheckBox,
    QProgressDialog, QComboBox,
)
from PyQt5.QtCore import Qt, QTimer, QDate, QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt5.QtGui import QColor

from ui.base_ui import BaseUI
from ui.styles import global_style, COLOR_DANGER, COLOR_TEXT_SECONDARY
from ui.tray_manager import TrayManager
from ui.app_icon import create_admin_icon
from core.role_manager import RoleManager, ROLE_ADMIN, ROLE_USER
from core.logger import setup_logger

logger = setup_logger('ui.admin_ui')


class AdminClient:
    """HTTP-клиент для общения с сервером монитора."""

    def __init__(self, base_url: str = "https://localhost:8765"):
        self.base_url = base_url.rstrip("/")
        self.ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        self._token: str | None = None
        # Отключаем проверку SSL для самоподписанных сертификатов
        self._client = httpx.Client(verify=False, timeout=5)

    def _headers(self) -> dict:
        h = {}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _get(self, path: str):
        r = self._client.get(f"{self.base_url}{path}", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict):
        r = self._client.post(f"{self.base_url}{path}", json=data, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str):
        r = self._client.delete(f"{self.base_url}{path}", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def login(self, username: str, password: str) -> bool:
        """Авторизация. Отправляет запрос без токена."""
        try:
            r = self._client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": username, "password": password},
            )
            r.raise_for_status()
            resp = r.json()
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
        self.username_input = QLineEdit("admin")
        self.username_input.setPlaceholderText("admin")
        layout.addRow("Логин:", self.username_input)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("пароль")
        layout.addRow("Пароль:", self.password_input)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Войти")
        btn_ok.clicked.connect(self._accept)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

    def _accept(self):
        """Проверить поля перед закрытием."""
        if not self.username_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите логин")
            self.username_input.setFocus()
            return
        if not self.password_input.text():
            QMessageBox.warning(self, "Ошибка", "Введите пароль")
            self.password_input.setFocus()
            return
        self.accept()


class AdminUI(BaseUI):
    """Удалённый интерфейс администрирования.

    Подключается к серверу AppMonitor по HTTP/WebSocket.
    Добавляет:
    - Панель подключения к серверу
    - Выбор даты для просмотра активности
    - WebSocket для real-time обновлений
    """

    def __init__(self):
        logger.info('AdminUI.__init__: начало')
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
        self._server_history: list[str] = self._load_server_history()
        logger.info('AdminUI.__init__: поля инициализированы, вызываем super().__init__()')

        super().__init__()

        logger.info('AdminUI.__init__: super() готов, добавляем панели')
        # Устанавливаем иконку окна для панели задач
        icon = create_admin_icon()
        self.setWindowIcon(icon)
        # Принудительное обновление иконки в трее Windows
        QTimer.singleShot(0, lambda: self._force_window_icon(icon))
        self._init_tray()
        self._add_connection_panel()
        self._add_date_picker()
        self._apply_role_restrictions()
        # Показываем диалог выбора при запуске
        QTimer.singleShot(500, self._show_startup_dialog)
        logger.info('AdminUI.__init__: завершено')

    @staticmethod
    def _force_window_icon(icon):
        """Принудительно обновить иконку окна в панели задач Windows.

        Qt не всегда обновляет иконку в панели задач после setWindowIcon,
        особенно если окно уже было создано. Этот трюк переустанавливает
        иконку через атрибут NativeWindowHandles.
        """
        app = QApplication.instance()
        if app is None:
            return
        # Переустанавливаем иконку приложения (влияет на все окна)
        app.setWindowIcon(icon)

    # ── Панель подключения ──────────────────────────────────────────

    def _add_connection_panel(self):
        """Добавить панель подключения к серверу."""
        logger.info('AdminUI._add_connection_panel: начало')
        central = self.centralWidget()
        if central is None:
            logger.error('AdminUI._add_connection_panel: centralWidget() is None!')
            return
        layout = central.layout()
        if layout is None:
            logger.error('AdminUI._add_connection_panel: layout is None!')
            return
        logger.info('AdminUI._add_connection_panel: central виджет получен')

        # Вставляем панель подключения первой
        conn_widget = QWidget()
        conn_layout = QHBoxLayout(conn_widget)
        conn_layout.setContentsMargins(0, 0, 0, 8)

        conn_layout.addWidget(QLabel("Сервер:"))
        self.server_input = QComboBox()
        self.server_input.setEditable(True)
        self.server_input.setInsertPolicy(QComboBox.NoInsert)
        self.server_input.setPlaceholderText("https://IP:порт (например, https://192.168.1.100:8765)")
        # Загружаем историю подключений
        for addr in self._server_history:
            self.server_input.addItem(addr)
        if self._server_history:
            self.server_input.setCurrentText(self._server_history[0])
        else:
            self.server_input.setCurrentText("https://localhost:8765")
        conn_layout.addWidget(self.server_input)

        btn_connect = QPushButton("Подключиться")
        btn_connect.clicked.connect(self._connect)
        conn_layout.addWidget(btn_connect)

        btn_discover = QPushButton("Найти серверы")
        btn_discover.clicked.connect(self._discover_servers)
        conn_layout.addWidget(btn_discover)

        self.conn_status = QLabel("Не подключён")
        self.conn_status.setStyleSheet(f"color: {COLOR_DANGER};")
        conn_layout.addWidget(self.conn_status)

        conn_layout.addStretch()

        # Вставляем в начало layout
        layout.insertWidget(0, conn_widget)

    def _add_date_picker(self):
        """Добавить панель выбора даты."""
        logger.info('AdminUI._add_date_picker: начало')
        central = self.centralWidget()
        if central is None:
            logger.error('AdminUI._add_date_picker: centralWidget() is None!')
            return
        layout = central.layout()
        if layout is None:
            logger.error('AdminUI._add_date_picker: layout is None!')
            return

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

    # ── Трей ────────────────────────────────────────────────────────

    def _init_tray(self):
        """Создать иконку в системном трее."""
        logger.debug('AdminUI: инициализация трей-иконки')
        self.tray = TrayManager(self, icon=create_admin_icon())
        self.tray.show_requested.connect(self.show_and_raise)
        logger.debug('AdminUI: трей-иконка создана')

    def show_and_raise(self):
        """Показать окно и поднять на передний план."""
        self.show()
        self.raise_()
        self.activateWindow()

    # ── Подключение ─────────────────────────────────────────────────

    def _discover_servers(self):
        """Найти серверы AppMonitor в локальной сети через mDNS."""
        try:
            from zeroconf import Zeroconf, ServiceBrowser, ServiceListener

            class _Listener(ServiceListener):
                def __init__(self, callback):
                    self.callback = callback
                    self.found = []

                def add_service(self, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info:
                        addr = ".".join(str(b) for b in info.addresses[0])
                        port = info.port
                        hostname = info.properties.get(b"hostname", b"unknown").decode()
                        self.found.append({"address": f"{addr}:{port}", "hostname": hostname})

                def remove_service(self, zc, type_, name):
                    pass

                def update_service(self, zc, type_, name):
                    pass

            listener = _Listener(None)
            zeroconf = Zeroconf()
            browser = ServiceBrowser(zeroconf, "_appmonitor._tcp.local.", listener)

            # Ждём 2 секунды для сбора ответов
            import time
            time.sleep(2)
            zeroconf.close()

            if listener.found:
                servers = "\n".join(
                    f"  {s['hostname']} — http://{s['address']}" for s in listener.found
                )
                QMessageBox.information(
                    self, "Найденные серверы",
                    f"Обнаружены серверы AppMonitor:\n{servers}\n\n"
                    f"Адрес подставлен в поле 'Сервер'. Нажмите 'Подключиться'."
                )
                # Подставляем первый найденный адрес с протоколом http
                if listener.found:
                    self.server_input.setText(f"http://{listener.found[0]['address']}")
            else:
                # Если mDNS не сработал, пробуем найти сервер через прямой HTTP-запрос
                self._discover_by_scan()
        except ImportError:
            self._discover_by_scan()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка поиска: {e}")

    def _discover_by_scan(self):
        """Поиск сервера через прямой HTTP-запрос к /api/status.
        Сканирует всю подсеть /24 с отображением прогресса.
        """
        try:
            import socket
            import httpx
            from PyQt5.QtCore import QThread, pyqtSignal

            class _ScanThread(QThread):
                found = pyqtSignal(str)
                progress = pyqtSignal(int, int, str)  # current, total, current_ip
                finished = pyqtSignal()

                def run(self):
                    # Получаем свой IP
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.settimeout(0.5)
                    try:
                        s.connect(("8.8.8.8", 80))
                        local_ip = s.getsockname()[0]
                    except Exception:
                        local_ip = "127.0.0.1"
                    s.close()

                    if local_ip == "127.0.0.1":
                        self.finished.emit()
                        return

                    prefix = ".".join(local_ip.split(".")[:3])
                    total = 254

                    for i in range(1, 255):
                        ip = f"{prefix}.{i}"
                        try:
                            url = f"http://{ip}:8765/api/status"
                            resp = httpx.get(url, timeout=0.3, verify=False)
                            if resp.status_code == 200:
                                data = resp.json()
                                if data.get("status") == "ok":
                                    self.found.emit(f"http://{ip}:8765")
                                    self.finished.emit()
                                    return
                        except Exception:
                            pass
                        self.progress.emit(i, total, ip)
                    self.finished.emit()

            self._scan_thread = _ScanThread()

            # Создаём окно прогресса
            self._progress = QProgressDialog(
                "Сканирование локальной сети...", "Отмена", 0, 254, self
            )
            self._progress.setWindowTitle("Поиск сервера")
            self._progress.setWindowModality(Qt.WindowModal)
            self._progress.setMinimumDuration(0)
            self._progress.setValue(0)
            self._progress.setAutoClose(True)
            self._progress.setAutoReset(True)

            def on_progress(current: int, total: int, current_ip: str):
                if self._progress.wasCanceled():
                    self._scan_thread.terminate()
                    self._scan_thread.wait()
                    return
                self._progress.setValue(current)
                self._progress.setLabelText(
                    f"Сканирование... {current}/{total}\n"
                    f"Проверен адрес {current_ip}"
                )

            def on_found(address: str):
                self._progress.close()
                self._on_server_found(address)

            def on_finished():
                if not self._progress.wasCanceled():
                    self._progress.close()
                    if not hasattr(self, '_server_found') or not self._server_found:
                        QMessageBox.information(
                            self, "Поиск серверов",
                            "Серверы AppMonitor не найдены в локальной сети.\n"
                            "Убедитесь, что AppMonitor запущен на другом компьютере "
                            "и они находятся в одной сети."
                        )

            self._server_found = False
            self._scan_thread.found.connect(on_found)
            self._scan_thread.progress.connect(on_progress)
            self._scan_thread.finished.connect(on_finished)
            self._scan_thread.start()

        except Exception as e:
            QMessageBox.warning(
                self, "Поиск серверов",
                "Серверы AppMonitor не найдены.\n"
                "Убедитесь, что AppMonitor запущен на другом компьютере "
                "и они находятся в одной сети.\n\n"
                f"Подробнее: {e}"
            )

    def _show_startup_dialog(self):
        """Показать диалог выбора при запуске: ввести адрес или найти сервер."""
        logger.info('AdminUI._show_startup_dialog: показываем диалог выбора')
        dialog = QDialog(self)
        dialog.setWindowTitle('Подключение к серверу')
        dialog.setMinimumWidth(450)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel('Выберите способ подключения к серверу AppMonitor:'))

        # Ручной ввод
        manual_group = QGroupBox('Ввести адрес вручную')
        manual_layout = QVBoxLayout(manual_group)
        addr_input = QComboBox()
        addr_input.setEditable(True)
        addr_input.setInsertPolicy(QComboBox.NoInsert)
        addr_input.setPlaceholderText('https://IP:порт (например, https://192.168.1.100:8765)')
        for addr in self._server_history:
            addr_input.addItem(addr)
        if self._server_history:
            addr_input.setCurrentText(self._server_history[0])
        else:
            addr_input.setCurrentText('https://localhost:8765')
        manual_layout.addWidget(addr_input)
        btn_manual = QPushButton('Подключиться')
        manual_layout.addWidget(btn_manual)
        layout.addWidget(manual_group)

        # Поиск в сети
        search_group = QGroupBox('Найти сервер в локальной сети')
        search_layout = QVBoxLayout(search_group)
        btn_search = QPushButton('Найти серверы')
        search_layout.addWidget(btn_search)
        layout.addWidget(search_group)

        # Отмена
        btn_cancel = QPushButton('Отмена')
        layout.addWidget(btn_cancel)

        def _on_manual():
            address = addr_input.currentText().strip()
            if not address:
                QMessageBox.warning(dialog, 'Ошибка', 'Введите адрес сервера')
                return
            if '://' not in address:
                address = f'http://{address}'
            dialog.accept()
            self.server_input.setCurrentText(address)
            self._connect()

        def _on_search():
            dialog.accept()
            self._discover_with_prompt()

        btn_manual.clicked.connect(_on_manual)
        btn_search.clicked.connect(_on_search)
        btn_cancel.clicked.connect(dialog.reject)

        dialog.exec_()

    def _discover_with_prompt(self):
        """Поиск сервера с диалогом: подключиться или искать дальше."""
        logger.info('AdminUI._discover_with_prompt: начало поиска')

        # Определяем свою подсеть автоматически
        subnet = self._detect_subnet()
        if subnet is None:
            QMessageBox.warning(
                self, 'Ошибка',
                'Не удалось определить локальную подсеть.\n'
                'Введите адрес сервера вручную.'
            )
            return

        self._scan_subnet = subnet
        self._scan_start_ip = 1
        self._start_scan()

    def _start_scan(self):
        """Запустить сканирование с self._scan_start_ip в self._scan_subnet."""
        subnet = self._scan_subnet
        start_ip = self._scan_start_ip

        try:
            import socket
            import httpx
            from PyQt5.QtCore import QThread, pyqtSignal

            class _ScanThread(QThread):
                found = pyqtSignal(str)
                progress = pyqtSignal(int, int, str)  # current, total, current_ip
                finished = pyqtSignal()

                def __init__(self, subnet_prefix: str, start_ip: int):
                    super().__init__()
                    self.subnet_prefix = subnet_prefix
                    self.start_ip = start_ip
                    self._canceled = False

                def cancel(self):
                    self._canceled = True

                def run(self):
                    total = 254
                    for i in range(self.start_ip, 255):
                        if self._canceled:
                            return
                        ip = f'{self.subnet_prefix}.{i}'
                        # Пробуем HTTP, затем HTTPS
                        for proto in ('http', 'https'):
                            try:
                                url = f'{proto}://{ip}:8765/api/status'
                                resp = httpx.get(url, timeout=0.3, verify=False)
                                if resp.status_code == 200:
                                    data = resp.json()
                                    if data.get('status') == 'ok':
                                        self.found.emit(f'{proto}://{ip}:8765')
                                        return
                            except Exception:
                                pass
                        self.progress.emit(i, total, ip)
                    self.finished.emit()

            self._scan_thread = _ScanThread(subnet, start_ip)

            # Создаём окно прогресса
            self._progress = QProgressDialog(
                f'Сканирование {subnet}.1-254...', 'Отмена', 0, 254, self
            )
            self._progress.setWindowTitle('Поиск сервера')
            self._progress.setWindowModality(Qt.WindowModal)
            self._progress.setMinimumDuration(0)
            self._progress.setValue(start_ip - 1)
            self._progress.setAutoClose(True)
            self._progress.setAutoReset(True)

            def on_progress(current: int, total: int, current_ip: str):
                if self._progress.wasCanceled():
                    self._scan_thread.cancel()
                    self._scan_thread.wait()
                    self._scan_in_progress = False
                    return
                self._progress.setValue(current)
                self._progress.setLabelText(
                    f'Сканирование... {current}/{total}\n'
                    f'Проверен адрес {current_ip}'
                )

            def on_found(address: str):
                self._progress.close()
                self.server_input.setCurrentText(address)
                # Кастомный диалог с двумя кнопками
                msg = QMessageBox(self)
                msg.setWindowTitle('Сервер найден')
                msg.setText(f'Обнаружен сервер AppMonitor по адресу:\n{address}')
                btn_connect = msg.addButton('Подключиться', QMessageBox.AcceptRole)
                btn_search_more = msg.addButton('Искать дальше', QMessageBox.ActionRole)
                msg.setDefaultButton(btn_connect)
                msg.exec_()

                if msg.clickedButton() == btn_connect:
                    self._connect()
                else:
                    # Ищем дальше — продолжаем с текущего IP+1
                    self._scan_start_ip = self._scan_thread.start_ip + 1
                    self._start_scan()

            def on_finished():
                if not self._progress.wasCanceled():
                    self._progress.close()
                    QMessageBox.information(
                        self, 'Поиск завершён',
                        f'Серверы AppMonitor не найдены в подсети {subnet}.0/24.\n'
                        'Попробуйте указать другой диапазон или ввести адрес вручную.'
                    )

            self._scan_in_progress = True
            self._scan_thread.found.connect(on_found)
            self._scan_thread.progress.connect(on_progress)
            self._scan_thread.finished.connect(on_finished)
            self._scan_thread.start()

        except Exception as e:
            self._scan_in_progress = False
            logger.error(f'AdminUI._start_scan: ошибка поиска: {e}', exc_info=True)
            QMessageBox.warning(
                self, 'Ошибка поиска',
                f'Не удалось выполнить поиск: {e}'
            )

    @staticmethod
    def _detect_subnet() -> str | None:
        """Определить локальную подсеть (первые 3 октета)."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
                if local_ip != '127.0.0.1':
                    return '.'.join(local_ip.split('.')[:3])
            except Exception:
                pass
            s.close()
        except Exception:
            pass
        return None

    def _on_server_found(self, address: str):
        """Обработчик найденного сервера при ручном сканировании."""
        self._server_found = True
        self.server_input.setCurrentText(address)
        QMessageBox.information(
            self, "Сервер найден",
            f"Сервер AppMonitor найден по адресу:\n{address}\n\n"
            f"Нажмите 'Подключиться' для входа."
        )

    def _load_server_history(self) -> list[str]:
        """Загрузить историю серверов из файла."""
        import json
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'server_history.json')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data[:10]  # не больше 10 записей
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return []

    def _save_server_address(self, address: str):
        """Сохранить адрес сервера в историю."""
        import json
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'server_history.json')
        history = self._load_server_history()
        # Убираем дубликат, если был
        if address in history:
            history.remove(address)
        # Добавляем в начало
        history.insert(0, address)
        # Оставляем не больше 10
        history = history[:10]
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            # Обновляем комбобокс
            self.server_input.clear()
            for addr in history:
                self.server_input.addItem(addr)
            self.server_input.setCurrentText(address)
        except Exception as e:
            logger.warning(f'Не удалось сохранить историю серверов: {e}')

    def _connect(self):
        """Подключиться к серверу."""
        logger.info('AdminUI._connect: начало')
        address = self.server_input.currentText().strip()
        logger.info(f'AdminUI._connect: адрес = "{address}"')
        if not address:
            QMessageBox.warning(self, "Ошибка", "Введите адрес сервера")
            return
        if "://" not in address:
            address = f"http://{address}"
            logger.info(f'AdminUI._connect: добавлен протокол -> {address}')
        self.api = AdminClient(address)
        try:
            logger.info('AdminUI._connect: запрос статуса...')
            status = self.api.get_status()
            logger.info(f'AdminUI._connect: статус получен: {status}')
            self.conn_status.setText(
                f"Подключён (аптайм: {status['uptime_seconds']}с, приложений: {status['monitored_apps']})"
            )
            self.conn_status.setStyleSheet("color: green;")
            # Авторизация — всегда показываем диалог
            logger.info('AdminUI._connect: запрос авторизации...')
            if not self._login():
                logger.warning('AdminUI._connect: авторизация не пройдена')
                self.api = None
                self.conn_status.setText("Ошибка авторизации")
                self.conn_status.setStyleSheet(f"color: {COLOR_DANGER};")
                return
            logger.info('AdminUI._connect: авторизация успешна, обновляем данные')
            # Сохраняем адрес в историю
            self._save_server_address(address)
            self._refresh_all()
            self._connect_ws()
        except Exception as e:
            logger.error(f'AdminUI._connect: ошибка: {e}', exc_info=True)
            self.conn_status.setText(f"Ошибка: {e}")
            self.conn_status.setStyleSheet(f"color: {COLOR_DANGER};")
            self.api = None

    def _login(self) -> bool:
        """Запросить логин/пароль у пользователя."""
        logger.info('AdminUI._login: показываем диалог входа')
        dialog = _AdminLoginDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            logger.info('AdminUI._login: пользователь отменил вход')
            return False
        username = dialog.username_input.text()
        logger.info(f'AdminUI._login: попытка входа как "{username}"')
        result = self.api.login(username, dialog.password_input.text())
        logger.info(f'AdminUI._login: результат = {result}')
        return result

    def _connect_ws(self):
        """Подключение к WebSocket."""
        logger.info('AdminUI._connect_ws: начало')
        try:
            class WsWorker(QThread):
                message_received = pyqtSignal(str)
                disconnected = pyqtSignal()

                def __init__(self, url):
                    super().__init__()
                    self.url = url
                    self._running = True

                def run(self):
                    try:
                        import websockets
                        import ssl
                        async def _listen():
                            try:
                                # Создаём SSL-контекст без проверки сертификата
                                ssl_context = ssl.create_default_context()
                                ssl_context.check_hostname = False
                                ssl_context.verify_mode = ssl.CERT_NONE

                                async with websockets.connect(self.url, ssl=ssl_context) as ws:
                                    self.message_received.emit('{"type":"connected"}')
                                    while self._running:
                                        try:
                                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                                            self.message_received.emit(msg)
                                        except asyncio.TimeoutError:
                                            try:
                                                await ws.send(json.dumps({"action": "ping"}))
                                            except Exception:
                                                break
                            except Exception as e:
                                logger.warning(f'WebSocket ошибка: {e}')
                            finally:
                                self.disconnected.emit()

                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(_listen())
                    except ImportError:
                        logger.debug("websockets не установлен")

                def stop(self):
                    self._running = False

            ws_url = f"{self.api.ws_url}/ws"
            logger.info(f'AdminUI._connect_ws: URL = {ws_url}')
            self._ws_worker = WsWorker(ws_url)
            self._ws_worker.message_received.connect(self._on_ws_message)
            self._ws_worker.disconnected.connect(self._on_ws_disconnected)
            self._ws_worker.start()
            logger.info('AdminUI._connect_ws: WebSocket запущен')
        except Exception as e:
            logger.warning(f'AdminUI._connect_ws: ошибка создания WebSocket: {e}')

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
        logger.info(f'AdminUI._refresh_activity_tab: дата={self._current_date}')
        if not self.api:
            logger.info('AdminUI._refresh_activity_tab: нет api')
            return
        try:
            is_today = (self._current_date == datetime.date.today().isoformat())
            logger.info(f'AdminUI._refresh_activity_tab: is_today={is_today}')
            if is_today:
                activity = self.api.get_today_activity()
            else:
                activity = self.api.get_activity_by_date(self._current_date)
            logger.info(f'AdminUI._refresh_activity_tab: получено {len(activity)} записей')
        except Exception as e:
            logger.error(f'AdminUI._refresh_activity_tab: ошибка получения: {e}', exc_info=True)
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

            hours = item['duration_seconds'] // 3600
            minutes = (item['duration_seconds'] % 3600) // 60
            secs = item['duration_seconds'] % 60
            time_str = f'{hours}:{minutes:02d}:{secs:02d}'
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignCenter)
            time_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.activity_table.setItem(i, 2, time_item)

            limit = limits.get(sys_id)
            limit_item = QTableWidgetItem()
            if limit and limit['enabled']:
                exceeded = item['duration_seconds'] // 60 >= limit['limit_minutes']
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
        dialog = AdminSettingsDialog(self.api, self)
        dialog.exec_()
        self._refresh_all()

    def _open_stats(self):
        """Открыть окно статистики (через API)."""
        if not self.api:
            QMessageBox.warning(self, "Ошибка", "Сначала подключитесь к серверу")
            return
        from ui.dialogs.stats_dialog import StatsDialog
        dialog = StatsDialog(self, self)
        dialog.exec_()

    def _refresh_all(self):
        """Обновить все вкладки с учётом выбранной даты."""
        logger.info('AdminUI._refresh_all: начало')
        if not self.api:
            logger.info('AdminUI._refresh_all: нет api, пропускаем')
            return
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
        logger.info('AdminUI._refresh_all: завершено')

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
