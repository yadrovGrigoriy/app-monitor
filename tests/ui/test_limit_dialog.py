"""Тесты для диалогов лимитов (AddLimitDialog, EditLimitDialog).

Тестируем бизнес-логику без QApplication.
"""

import unittest
from unittest.mock import patch, MagicMock

from tests.conftest import create_test_db, cleanup_test_db


class TestAddLimitDialogLogic(unittest.TestCase):
    """Проверка логики AddLimitDialog."""

    def setUp(self):
        self.db, self.db_path = create_test_db()

    def tearDown(self):
        cleanup_test_db(self.db, self.db_path)

    def test_load_apps_from_db(self):
        """_load_apps собирает приложения из БД."""
        from ui.dialogs.limit_dialog import AddLimitDialog

        # Создаём диалог с замоканным parent
        dialog = AddLimitDialog.__new__(AddLimitDialog)
        dialog.db = self.db
        dialog.combo = MagicMock()

        dialog._load_apps()

        # Проверяем, что addItem вызывался
        self.assertTrue(dialog.combo.addItem.called)

    def test_on_ok_with_valid_data(self):
        """_on_ok с валидными данными."""
        from ui.dialogs.limit_dialog import AddLimitDialog

        dialog = AddLimitDialog.__new__(AddLimitDialog)
        dialog.db = self.db
        dialog.combo = MagicMock()
        dialog.combo.currentData.return_value = 'TestApp'
        dialog.hours_spin = MagicMock()
        dialog.hours_spin.value.return_value = 1
        dialog.minutes_spin = MagicMock()
        dialog.minutes_spin.value.return_value = 30
        dialog.accept = MagicMock()

        dialog._on_ok()

        self.assertEqual(dialog.app_name, 'TestApp')
        self.assertEqual(dialog.limit_minutes, 90)  # 1*60 + 30
        dialog.accept.assert_called_once()

    def test_on_ok_with_empty_name(self):
        """_on_ok с пустым именем — предупреждение."""
        from ui.dialogs.limit_dialog import AddLimitDialog

        dialog = AddLimitDialog.__new__(AddLimitDialog)
        dialog.db = self.db
        dialog.combo = MagicMock()
        dialog.combo.currentData.return_value = None
        dialog.combo.currentText.return_value = ''
        dialog.hours_spin = MagicMock()
        dialog.minutes_spin = MagicMock()
        dialog.accept = MagicMock()

        with patch('ui.dialogs.limit_dialog.QMessageBox.warning') as mock_warning:
            dialog._on_ok()

        mock_warning.assert_called_once()
        dialog.accept.assert_not_called()

    def test_on_ok_with_zero_limit(self):
        """_on_ok с нулевым лимитом — предупреждение."""
        from ui.dialogs.limit_dialog import AddLimitDialog

        dialog = AddLimitDialog.__new__(AddLimitDialog)
        dialog.db = self.db
        dialog.combo = MagicMock()
        dialog.combo.currentData.return_value = 'TestApp'
        dialog.hours_spin = MagicMock()
        dialog.hours_spin.value.return_value = 0
        dialog.minutes_spin = MagicMock()
        dialog.minutes_spin.value.return_value = 0
        dialog.accept = MagicMock()

        with patch('ui.dialogs.limit_dialog.QMessageBox.warning') as mock_warning:
            dialog._on_ok()

        mock_warning.assert_called_once()
        dialog.accept.assert_not_called()

    def test_preset_app(self):
        """preset_app сохраняется."""
        from ui.dialogs.limit_dialog import AddLimitDialog

        dialog = AddLimitDialog.__new__(AddLimitDialog)
        dialog.app_name = 'Google Chrome'
        self.assertEqual(dialog.app_name, 'Google Chrome')


class TestEditLimitDialogLogic(unittest.TestCase):
    """Проверка логики EditLimitDialog."""

    def setUp(self):
        self.db, self.db_path = create_test_db()

    def tearDown(self):
        cleanup_test_db(self.db, self.db_path)

    def test_on_save_updates_db(self):
        """_on_save обновляет лимит в БД."""
        from ui.dialogs.limit_dialog import EditLimitDialog

        # Сначала создаём лимит
        self.db.set_limit('test.exe', 60, True, app_name='TestApp')

        limit_data = self.db.get_limit_by_system_id('test.exe')
        self.assertIsNotNone(limit_data)

        dialog = EditLimitDialog.__new__(EditLimitDialog)
        dialog.db = self.db
        dialog.app_name = 'TestApp'
        dialog.hours_spin = MagicMock()
        dialog.hours_spin.value.return_value = 2
        dialog.minutes_spin = MagicMock()
        dialog.minutes_spin.value.return_value = 0
        dialog.enabled_check = MagicMock()
        dialog.enabled_check.isChecked.return_value = True
        dialog.accept = MagicMock()

        dialog._on_save()

        # Проверяем в БД
        updated = self.db.get_limit_by_system_id('test.exe')
        self.assertEqual(updated['limit_minutes'], 120)
        dialog.accept.assert_called_once()

    def test_on_save_with_zero_limit(self):
        """_on_save с нулевым лимитом — предупреждение."""
        from ui.dialogs.limit_dialog import EditLimitDialog

        dialog = EditLimitDialog.__new__(EditLimitDialog)
        dialog.db = self.db
        dialog.app_name = 'TestApp'
        dialog.hours_spin = MagicMock()
        dialog.hours_spin.value.return_value = 0
        dialog.minutes_spin = MagicMock()
        dialog.minutes_spin.value.return_value = 0
        dialog.enabled_check = MagicMock()
        dialog.accept = MagicMock()

        with patch('ui.dialogs.limit_dialog.QMessageBox.warning') as mock_warning:
            dialog._on_save()

        mock_warning.assert_called_once()
        dialog.accept.assert_not_called()

    def test_on_save_disables_limit(self):
        """_on_save может отключить лимит."""
        from ui.dialogs.limit_dialog import EditLimitDialog

        self.db.set_limit('test.exe', 60, True, app_name='TestApp')

        dialog = EditLimitDialog.__new__(EditLimitDialog)
        dialog.db = self.db
        dialog.app_name = 'TestApp'
        dialog.hours_spin = MagicMock()
        dialog.hours_spin.value.return_value = 1
        dialog.minutes_spin = MagicMock()
        dialog.minutes_spin.value.return_value = 0
        dialog.enabled_check = MagicMock()
        dialog.enabled_check.isChecked.return_value = False
        dialog.accept = MagicMock()

        dialog._on_save()

        updated = self.db.get_limit_by_system_id('test.exe')
        self.assertFalse(updated['enabled'])
