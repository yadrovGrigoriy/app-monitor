from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QFormLayout, QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
import datetime
from core.database import Database
from core.auth import AuthManager
from core.autostart import AutostartManager
from core.logger import setup_logger
from ui.styles import global_style, COLOR_DANGER

from ui.dialogs.auth_dialogs import AuthDialog, RegisterDialog
from ui.dialogs.limit_dialog import AddLimitDialog, EditLimitDialog
from ui.dialogs.update_dialog import UpdateDialog
from ui.theme_manager import THEME_LIGHT, THEME_DARK, THEME_SETTING_KEY, apply_theme

logger = setup_logger('ui.settings')


class SettingsDialog(QDialog):
    def __init__(self, db: Database, parent=None, skip_auth: bool = False):
        super().__init__(parent)
        self.db = db
        self.auth = AuthManager(db)
        self._authorized = skip_auth
        self.autostart = AutostartManager()
        logger.debug('SettingsDialog __init__')
        if not skip_auth and not self._authenticate():
            self.reject()
            raise Exception('_abort_init')
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
            dialog = AuthDialog(self, attempt)
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
        dialog = RegisterDialog(self)
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
        self.setMinimumSize(620, 520)
        self.resize(680, 560)
        self.setStyleSheet(global_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        tabs = QTabWidget()
        layout.addWidget(tabs, stretch=1)

        # ── Вкладка лимитов ─────────────────────────────────────────
        limits_tab = QWidget()
        limits_layout = QVBoxLayout(limits_tab)
        limits_layout.setContentsMargins(4, 4, 4, 4)
        limits_layout.setSpacing(10)
        tabs.addTab(limits_tab, 'Лимиты')

        limits_layout.addWidget(QLabel('Установите лимиты времени для приложений:'))

        self.limits_table = QTableWidget()
        self.limits_table.setColumnCount(5)
        self.limits_table.setHorizontalHeaderLabels(['Приложение', 'Лимит (мин)', 'Осталось', 'Включено', ''])
        self.limits_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.limits_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.limits_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.limits_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.limits_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.limits_table.setAlternatingRowColors(True)
        self.limits_table.setShowGrid(False)
        self.limits_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.limits_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.limits_table.verticalHeader().setVisible(False)
        self.limits_table.resizeRowsToContents()
        self.limits_table.cellDoubleClicked.connect(self._edit_limit)
        limits_layout.addWidget(self.limits_table, stretch=1)

        btn_add_limit = QPushButton('Добавить лимит')
        btn_add_limit.clicked.connect(self._add_limit)
        btn_margin = QHBoxLayout()
        btn_margin.setContentsMargins(0, 0, 0, 4)
        btn_margin.addWidget(btn_add_limit)
        btn_margin.addStretch()
        limits_layout.addLayout(btn_margin)

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

        # ── Группа темы ─────────────────────────────────────────────
        theme_group = QGroupBox('Оформление')
        theme_layout = QFormLayout(theme_group)
        theme_layout.setSpacing(6)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem('Светлая', THEME_LIGHT)
        self.theme_combo.addItem('Тёмная', THEME_DARK)
        theme_layout.addRow('Тема:', self.theme_combo)

        general_layout.addWidget(theme_group)

        # ── Группа обновлений ─────────────────────────────────────────
        update_group = QGroupBox('Обновления')
        update_group_layout = QVBoxLayout(update_group)
        btn_check_update = QPushButton('Проверить обновления')
        btn_check_update.clicked.connect(self._check_updates)
        update_group_layout.addWidget(btn_check_update)
        general_layout.addWidget(update_group)

        general_layout.addStretch()

        # ── Вкладка исключений ──────────────────────────────────────
        exclude_tab = QWidget()
        exclude_layout = QVBoxLayout(exclude_tab)
        exclude_layout.setContentsMargins(4, 4, 4, 4)
        exclude_layout.setSpacing(10)
        tabs.addTab(exclude_tab, 'Исключения')

        exclude_layout.addWidget(QLabel('Приложения из этого списка не будут отслеживаться:'))

        self.exclude_table = QTableWidget()
        self.exclude_table.setColumnCount(3)
        self.exclude_table.setHorizontalHeaderLabels(['ID (имя процесса)', 'Отображаемое имя', ''])
        self.exclude_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.exclude_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.exclude_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.exclude_table.setAlternatingRowColors(True)
        self.exclude_table.setShowGrid(False)
        self.exclude_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.exclude_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.exclude_table.verticalHeader().setVisible(False)
        self.exclude_table.cellDoubleClicked.connect(self._on_exclude_table_click)
        exclude_layout.addWidget(self.exclude_table, stretch=1)

        btn_exclude_layout = QHBoxLayout()
        btn_add_exclude = QPushButton('Добавить исключение')
        btn_add_exclude.clicked.connect(self._add_exclude)
        btn_exclude_layout.addWidget(btn_add_exclude)
        btn_exclude_layout.addStretch()
        exclude_layout.addLayout(btn_exclude_layout)

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
        today_activity = self.db.get_daily_activity(datetime.date.today().isoformat())
        usage = {a['system_id'].lower(): a['total_seconds'] // 60 for a in today_activity}
        apps = {a['system_id'].lower(): a for a in self.db.get_all_apps()}

        self.limits_table.setRowCount(len(limits))
        for i, limit in enumerate(limits):
            sys_id = limit['system_id'].lower()
            # Определяем цвет подсветки строки
            row_bg = None
            if limit['enabled']:
                used = usage.get(sys_id, 0)
                left = max(0, limit['limit_minutes'] - used)
                if left == 0:
                    row_bg = QColor('#fde7e9')  # красный — лимит исчерпан
                elif left < 15:
                    row_bg = QColor('#fff8e1')  # жёлтый — осталось меньше 15 мин

            # Приложение
            name_item = QTableWidgetItem(limit['app_name'])

            if row_bg:
                name_item.setBackground(row_bg)
            if limit['enabled'] and left == 0:
                name_item.setForeground(QColor(COLOR_DANGER))
            self.limits_table.setItem(i, 0, name_item)

            # Лимит (мин)
            limit_item = QTableWidgetItem(str(limit['limit_minutes']))
            limit_item.setTextAlignment(Qt.AlignCenter)
            if limit['enabled'] and left == 0:
                limit_item.setForeground(QColor(COLOR_DANGER))
            self.limits_table.setItem(i, 1, limit_item)

            # Оставшееся время
            remaining = QTableWidgetItem()
            remaining.setTextAlignment(Qt.AlignCenter)
            if limit['enabled']:
                used = usage.get(limit['app_name'], 0)
                left = max(0, limit['limit_minutes'] - used)
                remaining.setText(f'{left} мин')
                if left == 0:
                    remaining.setForeground(QColor(COLOR_DANGER))
                else:
                    remaining.setForeground(QColor('#107c10'))
            else:
                remaining.setText('—')
                remaining.setForeground(QColor('#616161'))
            if row_bg:
                remaining.setBackground(row_bg)
            self.limits_table.setItem(i, 2, remaining)

            # Включено
            enabled_item = QTableWidgetItem('✓' if limit['enabled'] else '—')
            enabled_item.setTextAlignment(Qt.AlignCenter)
            enabled_font = enabled_item.font()
            enabled_font.setBold(True)
            enabled_item.setFont(enabled_font)
            if limit['enabled'] and left == 0:
                enabled_item.setForeground(QColor(COLOR_DANGER))
            elif limit['enabled']:
                enabled_item.setForeground(QColor('#107c10'))
            else:
                enabled_item.setForeground(QColor('#616161'))
            if row_bg:
                enabled_item.setBackground(row_bg)
            self.limits_table.setItem(i, 3, enabled_item)

            # Кнопка удалить (текст)
            del_item = QTableWidgetItem('✕')
            del_item.setTextAlignment(Qt.AlignCenter)
            del_item.setForeground(QColor(COLOR_DANGER))
            del_font = del_item.font()
            del_font.setBold(True)
            del_item.setFont(del_font)
            if row_bg:
                del_item.setBackground(row_bg)
            self.limits_table.setItem(i, 4, del_item)

        self.limits_table.resizeRowsToContents()

    def _edit_limit(self, row: int, column: int):
        """Открыть диалог редактирования лимита."""
        app_name = self.limits_table.item(row, 0).text()
        limits = self.db.get_all_limits()
        limit_data = next((l for l in limits if l['app_name'] == app_name), None)
        if not limit_data:
            return

        if column == 4:
            # Клик на ✕ — удаляем
            reply = QMessageBox.question(
                self, 'Удаление лимита',
                f'Удалить лимит для "{app_name}"?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._delete_limit(app_name)
            return

        dialog = EditLimitDialog(self.db, limit_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self._refresh_limits_table()

    def _add_limit(self):
        dialog = AddLimitDialog(self.db, self)
        if dialog.exec_() == QDialog.Accepted and dialog.app_name:
            logger.info(f'Добавлен лимит: {dialog.app_name}')
            app = self.db.get_app_by_system_id(dialog.app_name.lower())
            if not app:
                all_apps = self.db.get_all_apps()
                for a in all_apps:
                    if a['app_name'].lower() == dialog.app_name.lower():
                        app = a
                        break
            system_id = app['system_id'] if app else dialog.app_name.lower()
            self.db.set_limit(system_id, dialog.limit_minutes, True, app_name=dialog.app_name)
            self._refresh_limits_table()

    def _delete_limit(self, app_name: str):
        logger.info(f'Удалён лимит: {app_name}')
        app = self.db.get_app_by_system_id(app_name.lower())
        if not app:
            all_apps = self.db.get_all_apps()
            for a in all_apps:
                if a['app_name'].lower() == app_name.lower():
                    app = a
                    break
        system_id = app['system_id'] if app else app_name.lower()
        self.db.delete_limit_by_system_id(system_id)
        self._refresh_limits_table()

    def _on_autostart_changed(self, state):
        if state == Qt.Checked:
            logger.info('Автозагрузка включена через настройки')
            self.autostart.enable()
        else:
            logger.info('Автозагрузка отключена через настройки')
            self.autostart.disable()

    def _check_updates(self):
        """Открыть диалог проверки обновлений."""
        dialog = UpdateDialog(self)
        dialog.exec_()

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

        # Сохраняем тему и применяем её сразу
        selected_theme = self.theme_combo.currentData()
        self.db.set_setting(THEME_SETTING_KEY, selected_theme)
        app = self.window().window().parent()
        # Ищем QApplication через родительскую цепочку
        from PyQt5.QtWidgets import QApplication
        qapp = QApplication.instance()
        if qapp:
            apply_theme(qapp, selected_theme)

        logger.debug('Настройки сохранены')
        self.accept()

    def _refresh_exclude_table(self):
        """Обновить таблицу исключений."""
        excluded = self.db.get_excluded_apps()
        self.exclude_table.setRowCount(len(excluded))
        for i, item in enumerate(excluded):
            sys_item = QTableWidgetItem(item['system_id'])
            sys_item.setForeground(QColor('#616161'))
            self.exclude_table.setItem(i, 0, sys_item)

            name_item = QTableWidgetItem(item.get('display_name', '') or '—')
            self.exclude_table.setItem(i, 1, name_item)

            del_item = QTableWidgetItem('✕')
            del_item.setTextAlignment(Qt.AlignCenter)
            del_item.setForeground(QColor(COLOR_DANGER))
            del_font = del_item.font()
            del_font.setBold(True)
            del_item.setFont(del_font)
            self.exclude_table.setItem(i, 2, del_item)

        self.exclude_table.resizeRowsToContents()

    def _on_exclude_table_click(self, row: int, column: int):
        """Обработка клика по таблице исключений."""
        if column == 2:
            system_id = self.exclude_table.item(row, 0).text()
            reply = QMessageBox.question(
                self, 'Удаление исключения',
                f'Убрать "{system_id}" из списка исключений?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.db.remove_excluded_app(system_id)
                self._refresh_exclude_table()

    def _add_exclude(self):
        """Диалог добавления исключения."""
        from ui.dialogs.limit_dialog import AddLimitDialog
        dialog = AddLimitDialog(self.db, self, title='Добавить исключение',
                                label='Введите имя процесса (system_id) для исключения:')
        if dialog.exec_() == QDialog.Accepted and dialog.app_name:
            self.db.add_excluded_app(dialog.app_name, dialog.app_name)
            self._refresh_exclude_table()
            logger.info(f'Добавлено исключение: {dialog.app_name}')

    def _load_settings(self):
        self.email_from.setText(self.db.get_setting('email_from'))
        self.email_password.setText(self.db.get_setting('email_password'))
        self.email_to.setText(self.db.get_setting('email_to'))
        self.smtp_server.setText(self.db.get_setting('smtp_server', 'smtp.gmail.com'))
        self.smtp_port.setValue(int(self.db.get_setting('smtp_port', '587')))
        self.report_enabled.setChecked(self.db.get_setting('report_enabled', '0') == '1')

        # Загружаем сохранённую тему
        saved_theme = self.db.get_setting(THEME_SETTING_KEY, THEME_LIGHT)
        idx = self.theme_combo.findData(saved_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        self._refresh_limits_table()
        self._refresh_exclude_table()
