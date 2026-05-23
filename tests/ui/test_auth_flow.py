"""Тесты для потока авторизации в BaseUI.

Проверяем логику _show_login_dialog, _open_auth_dialog,
_apply_role_restrictions и verify_local.
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock


class TestBaseUIAuthFlow(unittest.TestCase):
    """Проверка потока авторизации в BaseUI."""

    def setUp(self):
        """Создать экземпляр BaseUI с моками."""
        from ui.base_ui import BaseUI

        # Создаём экземпляр через __new__, чтобы избежать __init__
        self.ui = BaseUI.__new__(BaseUI)
        self.ui._role_manager = MagicMock()
        self.ui._settings_authorized = True
        self.ui._extensions = {}
        self.ui.bottom_bar = MagicMock()
        self.ui.activity_table = MagicMock()
        self.ui.tracked_table = MagicMock()
        self.ui.excluded_table = MagicMock()
        self.ui.tabs = MagicMock()
        self.ui.btn_add_exclude = MagicMock()

    def test_is_admin_returns_true_when_admin(self):
        """_is_admin возвращает True, если роль admin."""
        self.ui._role_manager.is_admin.return_value = True
        result = self.ui._is_admin()
        self.assertTrue(result)

    def test_is_admin_returns_false_when_user(self):
        """_is_admin возвращает False, если роль user."""
        self.ui._role_manager.is_admin.return_value = False
        result = self.ui._is_admin()
        self.assertFalse(result)

    def test_is_admin_returns_false_when_no_role_manager(self):
        """_is_admin возвращает False, если _role_manager = None."""
        self.ui._role_manager = None
        result = self.ui._is_admin()
        self.assertFalse(result)

    def test_open_auth_dialog_logout_when_admin(self):
        """_open_auth_dialog при роли admin — выход из админки."""
        self.ui._role_manager.is_admin.return_value = True
        self.ui._refresh_all = MagicMock()
        self.ui._apply_role_restrictions = MagicMock()

        self.ui._open_auth_dialog()

        self.ui._role_manager.set_role.assert_called_once()
        self.ui._apply_role_restrictions.assert_called_once()
        self.ui._refresh_all.assert_called_once()

    def test_open_auth_dialog_shows_login_when_user(self):
        """_open_auth_dialog при роли user — показывает диалог входа."""
        self.ui._role_manager.is_admin.return_value = False
        self.ui._show_login_dialog = MagicMock()

        self.ui._open_auth_dialog()

        self.ui._show_login_dialog.assert_called_once()

    @patch('ui.base_ui.QMessageBox.question')
    def test_show_login_dialog_no_admin_asks_create(self, mock_question):
        """Если админ не существует — спрашиваем, создать ли."""
        from PyQt5.QtWidgets import QMessageBox

        mock_question.return_value = QMessageBox.No
        self.ui.admin_exists = MagicMock(return_value=False)
        self.ui._show_login_dialog()

        mock_question.assert_called_once()

    @patch('ui.base_ui.QMessageBox.question')
    @patch('ui.base_ui.RegisterDialog')
    def test_show_login_dialog_register_admin(self, mock_reg_dialog, mock_question):
        """Если админ не существует и пользователь согласен — регистрируем."""
        from PyQt5.QtWidgets import QMessageBox

        mock_question.return_value = QMessageBox.Yes
        self.ui.admin_exists = MagicMock(return_value=False)
        self.ui.register_admin = MagicMock(return_value=True)
        self.ui._apply_role_restrictions = MagicMock()
        self.ui._refresh_all = MagicMock()

        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec_.return_value = True
        mock_dialog_instance.username_input.text.return_value = 'admin'
        mock_dialog_instance.password_input.text.return_value = 'pass123'
        mock_reg_dialog.return_value = mock_dialog_instance

        self.ui._show_login_dialog()

        self.ui.register_admin.assert_called_once_with('admin', 'pass123')
        self.ui._role_manager.set_role.assert_called_once()
        self.ui._apply_role_restrictions.assert_called_once()
        self.ui._refresh_all.assert_called_once()

    @patch('ui.base_ui.AuthDialog')
    def test_show_login_dialog_successful_login(self, mock_auth_dialog):
        """Успешная авторизация с правильными данными."""
        self.ui.admin_exists = MagicMock(return_value=True)
        self.ui.verify_local = MagicMock(return_value=True)
        self.ui._apply_role_restrictions = MagicMock()
        self.ui._refresh_all = MagicMock()

        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec_.return_value = True
        mock_dialog_instance.username_input.text.return_value = 'admin'
        mock_dialog_instance.password_input.text.return_value = 'pass123'
        mock_auth_dialog.return_value = mock_dialog_instance

        self.ui._show_login_dialog()

        self.ui.verify_local.assert_called_once_with('admin', 'pass123')
        self.ui._role_manager.set_role.assert_called_once()
        self.ui._apply_role_restrictions.assert_called_once()
        self.ui._refresh_all.assert_called_once()

    @patch('ui.base_ui.AuthDialog')
    @patch('ui.base_ui.QMessageBox.warning')
    def test_show_login_dialog_wrong_password(self, mock_warning, mock_auth_dialog):
        """Неверный пароль — предупреждение и повторный диалог."""
        self.ui.admin_exists = MagicMock(return_value=True)
        self.ui.verify_local = MagicMock(return_value=False)

        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec_.return_value = True
        mock_dialog_instance.username_input.text.return_value = 'admin'
        mock_dialog_instance.password_input.text.return_value = 'wrong'
        mock_auth_dialog.return_value = mock_dialog_instance

        self.ui._show_login_dialog()

        # verify_local вызывается 3 раза (3 попытки)
        self.assertEqual(self.ui.verify_local.call_count, 3)
        # warning вызывается 3 раза
        self.assertEqual(mock_warning.call_count, 3)

    def test_apply_role_restrictions_admin(self):
        """_apply_role_restrictions для admin — полный доступ."""
        self.ui._is_admin = MagicMock(return_value=True)
        self.ui._show_excluded_tab = MagicMock()

        self.ui._apply_role_restrictions()

        self.ui._show_excluded_tab.assert_called_once_with(True)
        self.ui.bottom_bar.set_auth_state.assert_called_once_with(True)
        self.ui.bottom_bar.btn_settings.setVisible.assert_called_once_with(True)
        self.ui.bottom_bar.btn_stats.setVisible.assert_called_once_with(True)
        self.ui.activity_table.setContextMenuPolicy.assert_called_once()
        self.ui.tracked_table.setContextMenuPolicy.assert_called_once()
        self.ui.excluded_table.setContextMenuPolicy.assert_called_once()

    def test_apply_role_restrictions_user(self):
        """_apply_role_restrictions для user — только просмотр."""
        self.ui._is_admin = MagicMock(return_value=False)
        self.ui._show_excluded_tab = MagicMock()

        self.ui._apply_role_restrictions()

        self.ui._show_excluded_tab.assert_called_once_with(False)
        self.ui.bottom_bar.set_auth_state.assert_called_once_with(False)
        self.ui.bottom_bar.btn_settings.setVisible.assert_called_once_with(False)
        self.ui.bottom_bar.btn_stats.setVisible.assert_called_once_with(False)


class TestAuthManagerLogic(unittest.TestCase):
    """Проверка логики AuthManager."""

    def setUp(self):
        """Создать AuthManager с моком БД."""
        from core.auth import AuthManager

        self.db = MagicMock()
        self.auth = AuthManager(self.db)

    def test_register_new_admin(self):
        """Регистрация нового администратора."""
        self.db.get_admin.return_value = None
        self.db.add_admin = MagicMock()

        result = self.auth.register('admin', 'pass123')

        self.assertTrue(result)
        self.db.add_admin.assert_called_once()

    def test_register_existing_admin(self):
        """Регистрация существующего администратора — False."""
        self.db.get_admin.return_value = {'username': 'admin'}

        result = self.auth.register('admin', 'pass123')

        self.assertFalse(result)

    def test_login_success(self):
        """Успешный вход."""
        from core.auth import hash_password

        self.db.get_admin.return_value = {
            'username': 'admin',
            'password_hash': hash_password('pass123'),
        }

        token = self.auth.login('admin', 'pass123')

        self.assertIsNotNone(token)
        self.assertIn(token, self.auth._tokens)

    def test_login_wrong_password(self):
        """Неверный пароль — None."""
        from core.auth import hash_password

        self.db.get_admin.return_value = {
            'username': 'admin',
            'password_hash': hash_password('correct_pass'),
        }

        token = self.auth.login('admin', 'wrong_pass')

        self.assertIsNone(token)

    def test_login_unknown_user(self):
        """Неизвестный пользователь — None."""
        self.db.get_admin.return_value = None

        token = self.auth.login('unknown', 'pass123')

        self.assertIsNone(token)

    def test_verify_local_success(self):
        """verify_local с правильными данными."""
        from core.auth import hash_password

        self.db.get_admin.return_value = {
            'username': 'admin',
            'password_hash': hash_password('pass123'),
        }

        result = self.auth.verify_local('admin', 'pass123')

        self.assertTrue(result)

    def test_verify_local_wrong_password(self):
        """verify_local с неверным паролем."""
        from core.auth import hash_password

        self.db.get_admin.return_value = {
            'username': 'admin',
            'password_hash': hash_password('correct_pass'),
        }

        result = self.auth.verify_local('admin', 'wrong_pass')

        self.assertFalse(result)

    def test_verify_local_unknown_user(self):
        """verify_local с неизвестным пользователем."""
        self.db.get_admin.return_value = None

        result = self.auth.verify_local('unknown', 'pass123')

        self.assertFalse(result)

    def test_validate_token_valid(self):
        """Проверка валидного токена."""
        from core.auth import hash_password

        self.db.get_admin.return_value = {
            'username': 'admin',
            'password_hash': hash_password('pass123'),
        }

        token = self.auth.login('admin', 'pass123')
        username = self.auth.validate_token(token)

        self.assertEqual(username, 'admin')

    def test_validate_token_invalid(self):
        """Проверка невалидного токена."""
        username = self.auth.validate_token('invalid_token')

        self.assertIsNone(username)

    def test_logout(self):
        """Выход — токен удаляется."""
        from core.auth import hash_password

        self.db.get_admin.return_value = {
            'username': 'admin',
            'password_hash': hash_password('pass123'),
        }

        token = self.auth.login('admin', 'pass123')
        self.auth.logout(token)

        self.assertNotIn(token, self.auth._tokens)


class TestPasswordHashing(unittest.TestCase):
    """Проверка хеширования паролей."""

    def test_hash_and_verify(self):
        """Хеширование и проверка пароля."""
        from core.auth import hash_password, verify_password

        password = 'my_secret_password'
        hashed = hash_password(password)

        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password('wrong_password', hashed))

    def test_hash_format(self):
        """Формат хеша: соль:хеш."""
        from core.auth import hash_password

        hashed = hash_password('pass123')

        self.assertIn(':', hashed)
        salt, h = hashed.split(':', 1)
        self.assertEqual(len(salt), 32)  # 16 байт = 32 hex символа
        self.assertEqual(len(h), 64)  # SHA-256 = 64 hex символа

    def test_verify_invalid_hash(self):
        """Проверка с некорректным хешем."""
        from core.auth import verify_password

        self.assertFalse(verify_password('pass', 'invalid_hash'))
        self.assertFalse(verify_password('pass', ''))


class TestAppUIAuthIntegration(unittest.TestCase):
    """Интеграционный тест: полный цикл авторизации через AppUI.

    Проверяет, что после авторизации:
    - Роль меняется на admin
    - Применяются ограничения роли
    - Приложение не падает (не выбрасывает исключений)
    """

    def setUp(self):
        """Создать AppUI с реальной БД и моками Qt."""
        from tests.conftest import create_test_db, cleanup_test_db
        from ui.app_ui import AppUI

        self.db, self.db_path = create_test_db()

        # Админ admin/admin создаётся автоматически в create_test_db()
        # Проверяем, что админ существует
        admin = self.db.get_admin('admin')
        self.assertIsNotNone(admin, 'Админ по умолчанию должен существовать')
        self._admin_username = 'admin'
        self._admin_password = 'admin'

        # Создаём AppUI через __new__, чтобы избежать Qt-инициализации
        self.app_ui = AppUI.__new__(AppUI)
        self.app_ui.db = self.db
        self.app_ui._monitor = None

        from core.auth import AuthManager
        from core.role_manager import RoleManager, ROLE_USER
        self.app_ui._auth_manager = AuthManager(self.db)
        self.app_ui._role_manager = RoleManager(self.db)
        self.app_ui._role_manager.set_role(ROLE_USER)
        self.app_ui._settings_authorized = True
        self.app_ui._notified_warning = set()
        self.app_ui._last_exceeded_notify = {}
        self.app_ui._extensions = {}

        # Мокаем Qt-зависимости
        self.app_ui.bottom_bar = MagicMock()
        self.app_ui.activity_table = MagicMock()
        self.app_ui.tracked_table = MagicMock()
        self.app_ui.excluded_table = MagicMock()
        self.app_ui.tabs = MagicMock()
        self.app_ui.btn_add_exclude = MagicMock()
        self.app_ui.excluded_tab = MagicMock()
        self.app_ui._refresh_all = MagicMock()
        self.app_ui._apply_role_restrictions = MagicMock()

    def tearDown(self):
        """Очистить временную БД."""
        from tests.conftest import cleanup_test_db
        cleanup_test_db(self.db, self.db_path)

    # ── Проверка verify_local ───────────────────────────────────────

    def test_verify_local_with_correct_credentials(self):
        """verify_local с правильными данными возвращает True."""
        result = self.app_ui.verify_local('admin', 'admin')
        self.assertTrue(result)

    def test_verify_local_with_wrong_password(self):
        """verify_local с неверным паролем возвращает False."""
        result = self.app_ui.verify_local('admin', 'wrong')
        self.assertFalse(result)

    def test_verify_local_with_unknown_user(self):
        """verify_local с неизвестным пользователем возвращает False."""
        result = self.app_ui.verify_local('unknown', 'pass123')
        self.assertFalse(result)

    # ── Проверка admin_exists ───────────────────────────────────────

    def test_admin_exists_returns_true(self):
        """admin_exists возвращает True, если админ есть в БД."""
        result = self.app_ui.admin_exists()
        self.assertTrue(result)

    def test_admin_exists_returns_false(self):
        """admin_exists возвращает False, если админа нет в БД."""
        conn = self.db._get_connection()
        try:
            conn.execute('DELETE FROM admins')
            conn.commit()
        finally:
            conn.close()
        result = self.app_ui.admin_exists()
        self.assertFalse(result)

    # ── Проверка register_admin ─────────────────────────────────────

    def test_register_admin_success(self):
        """register_admin создаёт нового администратора."""
        conn = self.db._get_connection()
        try:
            conn.execute('DELETE FROM admins')
            conn.commit()
        finally:
            conn.close()

        result = self.app_ui.register_admin('new_admin', 'new_pass')
        self.assertTrue(result)

        # Проверяем, что админ создан
        admin = self.db.get_admin('new_admin')
        self.assertIsNotNone(admin)
        self.assertEqual(admin['username'], 'new_admin')

    def test_register_admin_duplicate(self):
        """register_admin с существующим логином возвращает False."""
        result = self.app_ui.register_admin('admin', 'another_pass')
        self.assertFalse(result)

    # ── Проверка полного цикла авторизации ──────────────────────────

    @patch('ui.base_ui.AuthDialog')
    def test_full_auth_flow_sets_admin_role(self, mock_auth_dialog):
        """После успешной авторизации роль меняется на admin.

        Проверяет, что _show_login_dialog:
        1. Вызывает verify_local с правильными данными
        2. Устанавливает роль admin
        3. Применяет ограничения роли
        4. Обновляет UI
        5. Не выбрасывает исключений
        """
        # Настраиваем мок диалога
        mock_dialog = MagicMock()
        mock_dialog.exec_.return_value = True
        mock_dialog.username_input.text.return_value = 'admin'
        mock_dialog.password_input.text.return_value = 'admin'
        mock_auth_dialog.return_value = mock_dialog

        # Выполняем авторизацию
        try:
            self.app_ui._show_login_dialog()
        except Exception as e:
            self.fail(f'Авторизация вызвала исключение: {e}')

        # Проверяем, что роль изменилась на admin
        self.assertTrue(self.app_ui._role_manager.is_admin())

        # Проверяем, что _apply_role_restrictions был вызван
        self.app_ui._apply_role_restrictions.assert_called_once()

        # Проверяем, что _refresh_all был вызван
        self.app_ui._refresh_all.assert_called_once()

    @patch('ui.base_ui.AuthDialog')
    def test_full_auth_flow_with_wrong_password(self, mock_auth_dialog):
        """После 3 неудачных попыток роль остаётся user."""
        mock_dialog = MagicMock()
        mock_dialog.exec_.return_value = True
        mock_dialog.username_input.text.return_value = 'admin'
        mock_dialog.password_input.text.return_value = 'wrong_pass'
        mock_auth_dialog.return_value = mock_dialog

        # Мокаем QMessageBox.warning, чтобы не было GUI
        with patch('ui.base_ui.QMessageBox.warning'):
            # Выполняем авторизацию с неверным паролем
            try:
                self.app_ui._show_login_dialog()
            except Exception as e:
                self.fail(f'Авторизация вызвала исключение: {e}')

        # Проверяем, что роль осталась user
        self.assertFalse(self.app_ui._role_manager.is_admin())

    @patch('ui.base_ui.RegisterDialog')
    @patch('ui.base_ui.QMessageBox.question')
    def test_full_auth_flow_register_admin(self, mock_question, mock_reg_dialog):
        """После регистрации нового админа роль меняется на admin."""
        from PyQt5.QtWidgets import QMessageBox

        # Удаляем существующего админа
        conn = self.db._get_connection()
        try:
            conn.execute('DELETE FROM admins')
            conn.commit()
        finally:
            conn.close()

        mock_question.return_value = QMessageBox.Yes

        mock_dialog = MagicMock()
        mock_dialog.exec_.return_value = True
        mock_dialog.username_input.text.return_value = 'new_admin'
        mock_dialog.password_input.text.return_value = 'new_pass'
        mock_reg_dialog.return_value = mock_dialog

        # Выполняем регистрацию
        try:
            self.app_ui._show_login_dialog()
        except Exception as e:
            self.fail(f'Регистрация вызвала исключение: {e}')

        # Проверяем, что роль изменилась на admin
        self.assertTrue(self.app_ui._role_manager.is_admin())

        # Проверяем, что админ создан в БД
        admin = self.db.get_admin('new_admin')
        self.assertIsNotNone(admin)

    # ── Проверка logout ─────────────────────────────────────────────

    def test_logout_changes_role_to_user(self):
        """Выход из режима админа меняет роль на user."""
        # Сначала делаем админом
        self.app_ui._role_manager.set_role('admin')
        self.assertTrue(self.app_ui._role_manager.is_admin())

        # Выполняем выход
        self.app_ui._open_auth_dialog()

        # Проверяем, что роль изменилась на user
        self.assertFalse(self.app_ui._role_manager.is_admin())

if __name__ == '__main__':
    unittest.main()
