import os, json
base = "C:/Users/Григорий/code/AppMonitor"
json_path = os.path.join(base, "project_files.json")
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

data["ui/settings_dialog.py"] = """from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QSpinBox, QCheckBox,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QFormLayout, QInputDialog
)
from PyQt5.QtCore import Qt
from core.database import Database
from core.autostart import AutostartManager


class SettingsDialog(QDialog):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.autostart = AutostartManager()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        self.setWindowTitle('Настройки')
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        limits_tab = QWidget()
        limits_layout = QVBoxLayout(limits_tab)
        tabs.addTab(limits_tab, 'Лимиты')
        limits_layout.addWidget(QLabel('Установите лимиты времени для приложений:'))
        self.limits_table = QTableWidget()
        self.limits_table.setColumnCount(4)
        self.limits_table.setHorizontalHeaderLabels(['Приложение', 'Лимит (мин)', 'Включено', ''])
        self.limits_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.limits_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        limits_layout.addWidget(self.limits_table)
        btn_add_limit = QPushButton('Добавить лимит')
        btn_add_limit.clicked.connect(self._add_limit)
        limits_layout.addWidget(btn_add_limit)

        email_tab = QWidget()
        email_layout = QVBoxLayout(email_tab)
        tabs.addTab(email_tab, 'Почта')
        email_group = QGroupBox('Настройки отправки отчетов')
        email_form = QFormLayout(email_group)
        self.email_from = QLineEdit()
        self.email_from.setPlaceholderText('your_email@gmail.com')
        email_form.addRow('От кого:', self.email_from)
        self.email_password = QLineEdit()
        self.email_password.setEchoMode(QLineEdit.Password)
        self.email_password.setPlaceholderText('пароль приложения')
        email_form.addRow('Пароль:', self.email_password)
        self.email_to = QLineEdit()
        self.email_to.setPlaceholderText('report@example.com')
        email_form.addRow('Кому:', self.email_to)
        self.smtp_server = QLineEdit('smtp.gmail.com')
        email_form.addRow('SMTP сервер:', self.smtp_server)
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        email_form.addRow('SMTP порт:', self.smtp_port)
        self.report_enabled = QCheckBox('Отправлять ежедневный отчет')
        email_form.addRow(self.report_enabled)
        email_layout.addWidget(email_group)

        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        tabs.addTab(general_tab, 'Общие')
        self.autostart_check = QCheckBox('Запускать вместе с Windows')
        self.autostart_check.setChecked(self.autostart.is_autostart_enabled())
        self.autostart_check.stateChanged.connect(self._on_autostart_changed)
        general_layout.addWidget(self.autostart_check)
        general_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_save = QPushButton('Сохранить')
        btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(btn_save)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _load_settings(self):
        self.email_from.setText(self.db.get_setting('email_from'))
        self.email_password.setText(self.db.get_setting('email_password'))
        self.email_to.setText(self.db.get_setting('email_to'))
        self.smtp_server.setText(self.db.get_setting('smtp_server', 'smtp.gmail.com'))
        self.smtp_port.setValue(int(self.db.get_setting('smtp_port', '587')))
        self.report_enabled.setChecked(self.db.get_setting('report_enabled', '0') == '1')
        self._refresh_limits_table()

    def _refresh_limits_table(self):
        limits = self.db.get_all_limits()
        self.limits_table.setRowCount(len(limits))
        for i, limit in enumerate(limits):
            self.limits_table.setItem(i, 0, QTableWidgetItem(limit['app_name']))
            spin = QSpinBox()
            spin.setRange(1, 1440)
            spin.setValue(limit['limit_minutes'])
            self.limits_table.setCellWidget(i, 1, spin)
            check = QCheckBox()
            check.setChecked(bool(limit['enabled']))
            self.limits_table.setCellWidget(i, 2, check)
            btn_del = QPushButton('Удалить')
            btn_del.clicked.connect(lambda checked, name=limit['app_name']: self._delete_limit(name))
            self.limits_table.setCellWidget(i, 3, btn_del)

    def _add_limit(self):
        app_name, ok = QInputDialog.getText(self, 'Новый лимит', 'Введите имя приложения (например, chrome.exe):')
        if ok and app_name:
            self.db.set_limit(app_name.strip(), 60, True)
            self._refresh_limits_table()

    def _delete_limit(self, app_name: str):
        self.db.delete_limit(app_name)
        self._refresh_limits_table()

    def _on_autostart_changed(self, state):
        if state == Qt.Checked:
            self.autostart.enable()
        else:
            self.autostart.disable()

    def _save_settings(self):
        self.db.set_setting('email_from', self.email_from.text())
        self.db.set_setting('email_password', self.email_password.text())
        self.db.set_setting('email_to', self.email_to.text())
        self.db.set_setting('smtp_server', self.smtp_server.text())
        self.db.set_setting('smtp_port', str(self.smtp_port.value()))
        self.db.set_setting('report_enabled', '1' if self.report_enabled.isChecked() else '0')
        for i in range(self.limits_table.rowCount()):
            app_name = self.limits_table.item(i, 0).text()
            spin = self.limits_table.cellWidget(i, 1)
            check = self.limits_table.cellWidget(i, 2)
            if spin and check:
                self.db.set_limit(app_name, spin.value(), check.isChecked())
        self.accept()
"""

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)
print("OK")
