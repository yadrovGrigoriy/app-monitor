"""Тесты для SettingsDialog — диалога настроек.

Тестируем бизнес-логику без QApplication.
"""

import unittest
from unittest.mock import patch, MagicMock

from tests.conftest import create_test_db, cleanup_test_db


class TestSettingsDialogLogic(unittest.TestCase):
    """Проверка логики SettingsDialog."""

    def setUp(self):
        self.db, self.db_path = create_test_db()

    def tearDown(self):
        cleanup_test_db(self.db, self.db_path)

    # --- Авторизация ---

    def test_authenticate_no_admin(self):
        """Если админ не создан, _authenticate предлагает регистрацию."""
        from ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog.auth = MagicMock()
        dialog.auth.verify_local.return_value = True

        with patch('ui.dialogs.settings_dialog.QMessageBox.question',
                   return_value=65536):  # Yes
            with patch.object(dialog, '_register_admin', return_value=True):
                result = dialog._authenticate()

        self.assertTrue(result)

    def test_authenticate_no_admin_cancelled(self):
        """Если пользователь отказался создавать админа — False."""
        from ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog.auth = MagicMock()

        with patch('ui.dialogs.settings_dialog.QMessageBox.question',
                   return_value=65536):  # No
            result = dialog._authenticate()

        self.assertFalse(result)

    def test_authenticate_success(self):
        """Успешная авторизация."""
        from ui.dialogs.settings_dialog import SettingsDialog

        # Создаём админа
        from core.auth import AuthManager
        auth = AuthManager(self.db)
        auth.register('admin', 'pass123')

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog.auth = auth
        dialog._register_admin = MagicMock()

        with patch('ui.dialogs.settings_dialog.AuthDialog') as mock_auth_dialog:
            mock_instance = mock_auth_dialog.return_value
            mock_instance.exec_.return_value = 1  # Accepted
            mock_instance.username_input = MagicMock()
            mock_instance.username_input.text.return_value = 'admin'
            mock_instance.password_input = MagicMock()
            mock_instance.password_input.text.return_value = 'pass123'

            result = dialog._authenticate()

        self.assertTrue(result)
        self.assertTrue(dialog._authorized)

    def test_authenticate_failure(self):
        """Неудачная авторизация (3 попытки)."""
        from ui.dialogs.settings_dialog import SettingsDialog

        auth = MagicMock()
        auth.verify_local.return_value = False

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog.auth = auth
        dialog._register_admin = MagicMock()

        with patch('ui.dialogs.settings_dialog.AuthDialog') as mock_auth_dialog:
            mock_instance = mock_auth_dialog.return_value
            mock_instance.exec_.return_value = 1  # Accepted
            mock_instance.username_input = MagicMock()
            mock_instance.username_input.text.return_value = 'admin'
            mock_instance.password_input = MagicMock()
            mock_instance.password_input.text.return_value = 'wrong'

            with patch('ui.dialogs.settings_dialog.QMessageBox.warning'):
                result = dialog._authenticate()

        self.assertFalse(result)

    # --- Сохранение настроек ---

    def test_save_settings(self):
        """_save_settings записывает настройки в БД."""
        from ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog._authorized = True
        dialog.email_from = MagicMock()
        dialog.email_from.text.return_value = 'test@example.com'
        dialog.email_password = MagicMock()
        dialog.email_password.text.return_value = 'secret'
        dialog.email_to = MagicMock()
        dialog.email_to.text.return_value = 'admin@example.com'
        dialog.smtp_server = MagicMock()
        dialog.smtp_server.text.return_value = 'smtp.gmail.com'
        dialog.smtp_port = MagicMock()
        dialog.smtp_port.value.return_value = 587
        dialog.report_enabled = MagicMock()
        dialog.report_enabled.isChecked.return_value = True
        dialog.theme_combo = MagicMock()
        dialog.theme_combo.currentData.return_value = 'dark'
        dialog.accept = MagicMock()

        with patch('ui.dialogs.settings_dialog.apply_theme'):
            with patch('ui.dialogs.settings_dialog.QApplication') as mock_qapp:
                mock_qapp.instance.return_value = MagicMock()
                dialog._save_settings()

        self.assertEqual(self.db.get_setting('email_from'), 'test@example.com')
        self.assertEqual(self.db.get_setting('email_password'), 'secret')
        self.assertEqual(self.db.get_setting('email_to'), 'admin@example.com')
        self.assertEqual(self.db.get_setting('smtp_server'), 'smtp.gmail.com')
        self.assertEqual(self.db.get_setting('smtp_port'), '587')
        self.assertEqual(self.db.get_setting('report_enabled'), '1')

    def test_save_settings_without_auth(self):
        """Без авторизации сохранение не работает."""
        from ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog._authorized = False

        with patch('ui.dialogs.settings_dialog.QMessageBox.warning') as mock_warning:
            dialog._save_settings()

        mock_warning.assert_called_once()

    # --- Лимиты ---

    def test_add_limit(self):
        """Добавление лимита через _add_limit."""
        from ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog._refresh_limits_table = MagicMock()

        with patch('ui.dialogs.settings_dialog.AddLimitDialog') as mock_dialog:
            mock_instance = mock_dialog.return_value
            mock_instance.exec_.return_value = 1  # Accepted
            mock_instance.app_name = 'Spotify'
            mock_instance.limit_minutes = 30

            dialog._add_limit()

        limit = self.db.get_limit_by_system_id('spotify.exe')
        self.assertIsNotNone(limit)
        self.assertEqual(limit['limit_minutes'], 30)

    def test_delete_limit(self):
        """Удаление лимита."""
        from ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog._refresh_limits_table = MagicMock()

        dialog._delete_limit('Google Chrome')

        limit = self.db.get_limit_by_system_id('chrome.exe')
        self.assertIsNone(limit)

    # --- Исключения ---

    def test_add_exclude(self):
        """Добавление исключения."""
        from ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog._refresh_exclude_table = MagicMock()

        with patch('ui.dialogs.settings_dialog.AddLimitDialog') as mock_dialog:
            mock_instance = mock_dialog.return_value
            mock_instance.exec_.return_value = 1
            mock_instance.app_name = 'new_app.exe'

            dialog._add_exclude()

        excluded = self.db.get_excluded_apps()
        self.assertTrue(any(e['system_id'] == 'new_app.exe' for e in excluded))

    def test_on_exclude_table_click_delete(self):
        """Клик на ✕ удаляет исключение."""
        from ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog._refresh_exclude_table = MagicMock()
        dialog.exclude_table = MagicMock()
        dialog.exclude_table.item.return_value.text.return_value = 'calculator.exe'

        with patch('ui.dialogs.settings_dialog.QMessageBox.question',
                   return_value=65536):  # Yes
            dialog._on_exclude_table_click(0, 2)

        excluded = self.db.get_excluded_apps()
        self.assertFalse(any(e['system_id'] == 'calculator.exe' for e in excluded))

    # --- Автозагрузка ---

    def test_autostart_enable(self):
        """Включение автозагрузки."""
        from ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.autostart = MagicMock()

        dialog._on_autostart_changed(2)  # Qt.Checked

        dialog.autostart.enable.assert_called_once()

    def test_autostart_disable(self):
        """Отключение автозагрузки."""
        from ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.autostart = MagicMock()

        dialog._on_autostart_changed(0)  # Qt.Unchecked

        dialog.autostart.disable.assert_called_once()

    # --- Загрузка настроек ---

    def test_load_settings(self):
        """_load_settings загружает настройки из БД."""
        from ui.dialogs.settings_dialog import SettingsDialog

        # Сохраняем настройки
        self.db.set_setting('email_from', 'saved@example.com')
        self.db.set_setting('email_password', 'saved_pass')
        self.db.set_setting('email_to', 'saved_to@example.com')
        self.db.set_setting('smtp_server', 'smtp.test.com')
        self.db.set_setting('smtp_port', '465')
        self.db.set_setting('report_enabled', '1')

        dialog = SettingsDialog.__new__(SettingsDialog)
        dialog.db = self.db
        dialog.email_from = MagicMock()
        dialog.email_password = MagicMock()
        dialog.email_to = MagicMock()
        dialog.smtp_server = MagicMock()
        dialog.smtp_port = MagicMock()
        dialog.report_enabled = MagicMock()
        dialog.theme_combo = MagicMock()
        dialog.theme_combo.findData.return_value = 0
        dialog._refresh_limits_table = MagicMock()
        dialog._refresh_exclude_table = MagicMock()
        dialog._refresh_admins_table = MagicMock()

        dialog._load_settings()

        dialog.email_from.setText.assert_called_once_with('saved@example.com')
        dialog.email_password.setText.assert_called_once_with('saved_pass')
        dialog.email_to.setText.assert_called_once_with('saved_to@example.com')
        dialog.smtp_server.setText.assert_called_once_with('smtp.test.com')
        dialog.smtp_port.setValue.assert_called_once_with(465)
        dialog.report_enabled.setChecked.assert_called_once_with(True)
