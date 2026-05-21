import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel,
    QLineEdit, QGroupBox, QFormLayout, QMessageBox, QTabWidget,
    QSpinBox, QCheckBox, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import httpx

from core.logger import setup_logger

logger = setup_logger('client')


class ApiClient:
    """HTTP-клиент для общения с сервером AppMonitor."""

    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str):
        try:
            r = httpx.get(f"{self.base_url}{path}", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"GET {path}: {e}")
            raise

    def _post(self, path: str, data: dict):
        try:
            r = httpx.post(f"{self.base_url}{path}", json=data, timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"POST {path}: {e}")
            raise

    def _delete(self, path: str):
        try:
            r = httpx.delete(f"{self.base_url}{path}", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"DELETE {path}: {e}")
            raise

    def get_status(self) -> dict:
        return self._get("/api/status")

    def get_today_activity(self) -> list:
        return self._get("/api/activity/today")

    def get_activity_by_date(self, date: str) -> list:
        return self._get(f"/api/activity/date/{date}")

    def get_limits(self) -> list:
        return self._get("/api/limits")

    def set_limit(self, app_name: str, limit_minutes: int, enabled: bool = True):
        return self._post("/api/limits", {
            "app_name": app_name,
            "limit_minutes": limit_minutes,
            "enabled": enabled,
        })

    def delete_limit(self, app_name: str):
        return self._delete(f"/api/limits/{app_name}")

    def get_setting(self, key: str, default: str = "") -> str:
        return self._get(f"/api/settings/{key}?default={default}")

    def set_setting(self, key: str, value: str):
        return self._post("/api/settings", {"key": key, "value": value})


class ClientWindow(QMainWindow):
    UPDATE_INTERVAL_MS = 5000

    def __init__(self):
        super().__init__()
        self.api: ApiClient | None = None
        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        self.setWindowTitle("AppMonitor — удалённый клиент")
        self.setMinimumSize(700, 500)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Панель подключения
        conn_group = QGroupBox("Подключение к серверу")
        conn_layout = QHBoxLayout(conn_group)
        conn_layout.addWidget(QLabel("Адрес:"))
        self.server_input = QLineEdit("192.168.1.100:8765")
        self.server_input.setPlaceholderText("IP:порт (например, 192.168.1.100:8765)")
        conn_layout.addWidget(self.server_input)
        btn_connect = QPushButton("Подключиться")
        btn_connect.clicked.connect(self._connect)
        conn_layout.addWidget(btn_connect)
        self.status_label = QLabel("Не подключён")
        conn_layout.addWidget(self.status_label)
        layout.addWidget(conn_group)

        # Таблица активности
        title = QLabel("Активность приложений за сегодня")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Приложение", "Время", "Лимит"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_settings = QPushButton("Настройки")
        btn_settings.clicked.connect(self._open_settings)
        btn_layout.addWidget(btn_settings)
        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self._refresh)
        btn_layout.addWidget(btn_refresh)
        layout.addLayout(btn_layout)

    def _init_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(self.UPDATE_INTERVAL_MS)

    def _connect(self):
        address = self.server_input.text().strip()
        if not address:
            QMessageBox.warning(self, "Ошибка", "Введите адрес сервера")
            return
        if "://" not in address:
            address = f"http://{address}"
        self.api = ApiClient(address)
        try:
            status = self.api.get_status()
            self.status_label.setText(f"Подключён (аптайм: {status['uptime_seconds']}с, приложений: {status['monitored_apps']})")
            self.status_label.setStyleSheet("color: green;")
            logger.info(f"Подключено к {address}")
            self._refresh()
        except Exception as e:
            self.status_label.setText(f"Ошибка: {e}")
            self.status_label.setStyleSheet("color: red;")
            self.api = None
            logger.error(f"Не удалось подключиться к {address}: {e}")

    def _refresh(self):
        if not self.api:
            return
        try:
            activity = self.api.get_today_activity()
            limits = {l["app_name"]: l for l in self.api.get_limits()}
        except Exception:
            return

        self.table.setRowCount(len(activity))
        for i, item in enumerate(activity):
            self.table.setItem(i, 0, QTableWidgetItem(item["app_name"]))
            hours = item["duration_seconds"] // 3600
            minutes = (item["duration_seconds"] % 3600) // 60
            time_str = f"{hours} ч {minutes:02d} мин"
            self.table.setItem(i, 1, QTableWidgetItem(time_str))
            limit = limits.get(item["app_name"])
            if limit and limit["enabled"]:
                limit_str = f'{limit["limit_minutes"]} мин'
                if item["duration_seconds"] // 60 >= limit["limit_minutes"]:
                    limit_str += " (!)"
            else:
                limit_str = "нет"
            self.table.setItem(i, 2, QTableWidgetItem(limit_str))

    def _open_settings(self):
        if not self.api:
            QMessageBox.warning(self, "Ошибка", "Сначала подключитесь к серверу")
            return
        dialog = ClientSettingsDialog(self.api, self)
        dialog.exec_()
        self._refresh()


class ClientSettingsDialog(QWidget):
    def __init__(self, api: ApiClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Настройки — удалённый клиент")
        self.setMinimumSize(500, 400)
        self._init_ui()
        self._load()

    def _init_ui(self):
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
                self.limits_table.setItem(i, 0, QTableWidgetItem(limit["app_name"]))
                spin = QSpinBox()
                spin.setRange(1, 1440)
                spin.setValue(limit["limit_minutes"])
                self.limits_table.setCellWidget(i, 1, spin)
                check = QCheckBox()
                check.setChecked(bool(limit["enabled"]))
                self.limits_table.setCellWidget(i, 2, check)
                btn_del = QPushButton("Удалить")
                btn_del.clicked.connect(lambda checked, name=limit["app_name"]: self._delete_limit(name))
                self.limits_table.setCellWidget(i, 3, btn_del)

            self.email_from.setText(self.api.get_setting("email_from"))
            self.email_to.setText(self.api.get_setting("email_to"))
            self.smtp_server.setText(self.api.get_setting("smtp_server", "smtp.gmail.com"))
            self.smtp_port.setValue(int(self.api.get_setting("smtp_port", "587")))
            self.report_enabled.setChecked(self.api.get_setting("report_enabled", "0") == "1")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить настройки: {e}")

    def _add_limit(self):
        app_name, ok = QInputDialog.getText(self, "Новый лимит", "Имя приложения (например, chrome.exe):")
        if ok and app_name:
            try:
                self.api.set_limit(app_name.strip(), 60, True)
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
                    self.api.set_limit(app_name, spin.value(), check.isChecked())

            QMessageBox.information(self, "Готово", "Настройки сохранены")
            self.close()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AppMonitor Client")
    window = ClientWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
