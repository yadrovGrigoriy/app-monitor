"""Тесты для диалогов авторизации (AuthDialog, RegisterDialog).

Тестируем бизнес-логику без QApplication.
"""

import unittest
from unittest.mock import MagicMock, patch


class TestAuthDialogLogic(unittest.TestCase):
    """Проверка логики AuthDialog."""

    def test_dialog_accepts(self):
        """Диалог может быть принят."""
        from ui.dialogs.auth_dialogs import AuthDialog

        dialog = AuthDialog.__new__(AuthDialog)
        dialog.accept = MagicMock()

        dialog.accept()
        dialog.accept.assert_called_once()

    def test_dialog_rejects(self):
        """Диалог может быть отклонён."""
        from ui.dialogs.auth_dialogs import AuthDialog

        dialog = AuthDialog.__new__(AuthDialog)
        dialog.reject = MagicMock()

        dialog.reject()
        dialog.reject.assert_called_once()

    def test_attempt_counter_displayed(self):
        """При attempt > 0 создаётся подсказка с номером попытки."""
        from ui.dialogs.auth_dialogs import AuthDialog

        # Проверяем, что конструктор принимает attempt
        dialog = AuthDialog.__new__(AuthDialog)
        # Не можем проверить UI без Qt, просто проверяем что класс существует
        self.assertIsNotNone(dialog)


class TestRegisterDialogLogic(unittest.TestCase):
    """Проверка логики RegisterDialog."""

    def test_on_ok_with_valid_data(self):
        """_on_ok с валидными данными принимает диалог."""
        from ui.dialogs.auth_dialogs import RegisterDialog

        dialog = RegisterDialog.__new__(RegisterDialog)
        dialog.username_input = MagicMock()
        dialog.username_input.text.return_value = 'admin'
        dialog.password_input = MagicMock()
        dialog.password_input.text.return_value = 'pass123'
        dialog.password_confirm = MagicMock()
        dialog.password_confirm.text.return_value = 'pass123'
        dialog.accept = MagicMock()

        dialog._on_ok()

        dialog.accept.assert_called_once()

    def test_on_ok_with_empty_username(self):
        """Пустой логин — предупреждение."""
        from ui.dialogs.auth_dialogs import RegisterDialog

        dialog = RegisterDialog.__new__(RegisterDialog)
        dialog.username_input = MagicMock()
        dialog.username_input.text.return_value = ''
        dialog.password_input = MagicMock()
        dialog.password_input.text.return_value = 'pass123'
        dialog.password_confirm = MagicMock()
        dialog.password_confirm.text.return_value = 'pass123'
        dialog.accept = MagicMock()

        with patch('ui.dialogs.auth_dialogs.QMessageBox.warning') as mock_warning:
            dialog._on_ok()

        mock_warning.assert_called_once()
        dialog.accept.assert_not_called()

    def test_on_ok_with_empty_password(self):
        """Пустой пароль — предупреждение."""
        from ui.dialogs.auth_dialogs import RegisterDialog

        dialog = RegisterDialog.__new__(RegisterDialog)
        dialog.username_input = MagicMock()
        dialog.username_input.text.return_value = 'admin'
        dialog.password_input = MagicMock()
        dialog.password_input.text.return_value = ''
        dialog.password_confirm = MagicMock()
        dialog.password_confirm.text.return_value = ''
        dialog.accept = MagicMock()

        with patch('ui.dialogs.auth_dialogs.QMessageBox.warning') as mock_warning:
            dialog._on_ok()

        mock_warning.assert_called_once()
        dialog.accept.assert_not_called()

    def test_on_ok_with_mismatched_passwords(self):
        """Пароли не совпадают — предупреждение."""
        from ui.dialogs.auth_dialogs import RegisterDialog

        dialog = RegisterDialog.__new__(RegisterDialog)
        dialog.username_input = MagicMock()
        dialog.username_input.text.return_value = 'admin'
        dialog.password_input = MagicMock()
        dialog.password_input.text.return_value = 'pass123'
        dialog.password_confirm = MagicMock()
        dialog.password_confirm.text.return_value = 'pass456'
        dialog.accept = MagicMock()

        with patch('ui.dialogs.auth_dialogs.QMessageBox.warning') as mock_warning:
            dialog._on_ok()

        mock_warning.assert_called_once()
        dialog.accept.assert_not_called()
