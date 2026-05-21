from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QSpinBox, QCheckBox,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QFormLayout, QInputDialog,
    QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from core.database import Database
from core.auth import AuthManager
from core.autostart import AutostartManager
from core.logger import setup_logger

logger = setup_logger('ui.settings')

COLOR_DANGER = "#d13438"


class SettingsDialog(QDialog):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.auth = AuthManager(db)
        self._authorized = False
        self.autostart = AutostartManager()
        logger.debug('SettingsDialog __init__')
        if not self._authenticate():
            self.reject()
            return
        self._init_ui()
        self._load_settings()

    def _authenticate(self) -> bool:
        if not self.db.admin_exists():
            reply = QMessageBox.question(
                self, "Первый вход",
                "Администратор не настроен. Создать учётную запись?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return False
            return self._register_admin()

        for attempt in range(3):
            dialog = _AuthDialog(self, attempt)
            if dialog.exec_() != QDialog.Accepted:
                return False
            username = dialog.username_input.text()
            password = dialog.password_input.text()
            if self.auth.verify_local(username, password):
                self._authorized = True
                logger.info(f'Локальная авторизация: {username}')
                return True
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")
        return False

    def _register_admin(self) -> bool:
        dialog = _RegisterDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return False
        username = dialog.username_input.text()
        password = dialog.password_input.text()
        if self.auth.register(username, password):
            self._authorized = True
            logger.info(f'Создан администратор: {username}')
            return True
        QMessageBox.warning(self, "Ошибка", "Не удалось создать администратора")
        return False

    def _init_ui(self):
        self.setWindowTitle('Настройки')
        self.setMinimumSize(580, 480)
        self.resize(640, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        tabs = QTabWidget()
        layout.addWidget(tabs, stretch=1)

        # ── Вкладка лимитов ─────────────────────────────────────────
        limits_tab = QWidget()
        limits_layout = QVBoxLayout(limits_tab)
        limits_layout.setContentsMargins(0, 0, 0, 0)
        tabs.addTab(limits_tab, 'Лимиты')

        limits_layout.addWidget(QLabel('Установите лимиты времени для приложений:'))

        self.limits_table = QTableWidget()
        self.limits_table.setColumnCount(4)
        self.limits_table.setHorizontalHeaderLabels(['Приложение', 'Лимит (мин)', 'Включено', ''])
        self.limits_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.limits_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.limits_table.setAlternatingRowColors(True)
        self.limits_table.setShowGrid(False)
        self.limits_table.verticalHeader().setVisible(False)
        limits_layout.addWidget(self.limits_table, stretch=1)

        btn_add_limit = QPushButton('Добавить лимит')
        btn_add_limit.clicked.connect(self._add_limit)
        limits_layout.addWidget(btn_add_limit)

        # ── Вкладка почты ───────────────────────────────────────────
        email_tab = QWidget()
        email_layout = QVBoxLayout(email_tab)
        email_layout.setContentsMargins(0, 0, 0, 0)
        tabs.addTab(email_tab, 'Почта')

        email_group = QGroupBox('Настройки отправки отчётов')
        email_form = QFormLayout(email_group)
        email_form.setSpacing(6)

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

        self.report_enabled = QCheckBox('Отправлять ежедневный отчёт')
        email_form.addRow(self.report_enabled)

        email_layout.addWidget(email_group)
        email_layout.addStretch()

        # ── Вкладка общих ───────────────────────────────────────────
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setContentsMargins(0, 0, 0, 0)
        tabs.addTab(general_tab, 'Общие')

        general_group = QGroupBox('Системные')
        general_group_layout = QVBoxLayout(general_group)
        self.autostart_check = QCheckBox('Запускать вместе с Windows')
        self.autostart_check.setChecked(self.autostart.is_autostart_enabled())
        self.autostart_check.stateChanged.connect(self._on_autostart_changed)
        general_group_layout.addWidget(self.autostart_check)
        general_layout.addWidget(general_group)
        general_layout.addStretch()

        # ── Кнопки ──────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
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
            logger.info(f'Добавлен лимит: {app_name.strip()}')
            self.db.set_limit(app_name.strip(), 60, True)
            self._refresh_limits_table()

    def _delete_limit(self, app_name: str):
        logger.info(f'Удалён лимит: {app_name}')
        self.db.delete_limit(app_name)
        self._refresh_limits_table()

    def _on_autostart_changed(self, state):
        if state == Qt.Checked:
            logger.info('Автозагрузка включена через настройки')
            self.autostart.enable()
        else:
            logger.info('Автозагрузка отключена через настройки')
            self.autostart.disable()

    def _save_settings(self):
        if not self._authorized:
            QMessageBox.warning(self, "Ошибка", "Требуется авторизация")
            return
        logger.info('Сохранение настроек')
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
        logger.debug('Настройки сохранены')
        self.accept()


# ─── Диалог входа ────────────────────────────────────────────────────

class _AuthDialog(QDialog):
    def __init__(self, parent=None, attempt: int = 0):
        super().__init__(parent)
        self.setWindowTitle("Авторизация")
        self.setFixedSize(360, 200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        title = QLabel('Вход администратора')
        title_font = QFont('Segoe UI', 12, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)

        if attempt > 0:
            hint = QLabel(f'Попытка {attempt + 1} из 3')
            hint.setStyleSheet(f"color: {COLOR_DANGER};")
            layout.addWidget(hint)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Логин')
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('Пароль')
        layout.addWidget(self.password_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton('Войти')
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)


# ─── Диалог регистрации ──────────────────────────────────────────────

class _RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание администратора")
        self.setFixedSize(380, 280)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        title = QLabel('Создание администратора')
        title_font = QFont('Segoe UI', 12, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addWidget(QLabel('Придумайте логин и пароль для управления настройками:'))

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Логин')
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('Пароль')
        layout.addWidget(self.password_input)

        self.password_confirm = QLineEdit()
        self.password_confirm.setEchoMode(QLineEdit.Password)
        self.password_confirm.setPlaceholderText('Повторите пароль')
        layout.addWidget(self.password_confirm)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton('Создать')
        btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _on_ok(self):
        if not self.username_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите логин")
            return
        if not self.password_input.text():
            QMessageBox.warning(self, "Ошибка", "Введите пароль")
            return
        if self.password_input.text() != self.password_confirm.text():
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return
        self.accept()
