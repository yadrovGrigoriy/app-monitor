"""Тесты для MainWindow — главного окна приложения.

Тестируем бизнес-логику через прямые вызовы методов MainWindow,
без создания QApplication (PyQt5 не работает в терминале без GUI).
"""

import unittest
from unittest.mock import MagicMock, patch, Mock
import datetime

from tests.conftest import create_test_db, cleanup_test_db


class TestMainWindowDB(unittest.TestCase):
    """Проверка взаимодействия MainWindow с БД."""

    def setUp(self):
        self.db, self.db_path = create_test_db()

    def tearDown(self):
        cleanup_test_db(self.db, self.db_path)

    # --- Вкладка «Открытые приложения» ---

    def test_get_open_windows_empty_without_monitor(self):
        """Без монитора _get_open_windows возвращает пустой список."""
        # Создаём MainWindow без монитора
        from ui.main_window import MainWindow
        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window._monitor = None
        result = window._get_open_windows()
        self.assertEqual(result, [])

    def test_get_open_windows_with_monitor(self):
        """_get_open_windows возвращает открытые окна, исключая исключённые."""
        from ui.main_window import MainWindow

        # Мокаем импорты внутри _get_open_windows
        mock_win32gui = MagicMock()
        mock_win32process = MagicMock()
        mock_psutil = MagicMock()
        mock_win32api = MagicMock()

        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.GetWindowText.return_value = 'Chrome Browser'
        mock_win32process.GetWindowThreadProcessId.return_value = (0, 1234)

        mock_process = MagicMock()
        mock_process.name.return_value = 'chrome.exe'
        mock_process.exe.return_value = r'C:\Program Files\Google\Chrome\chrome.exe'
        mock_psutil.Process.return_value = mock_process

        mock_win32api.GetFileVersionInfo.side_effect = [
            [(0, 0)],
            'Google Chrome'
        ]

        # Заставляем EnumWindows вызвать колбэк
        def enum_windows(callback, _):
            callback(12345, 0)
        mock_win32gui.EnumWindows.side_effect = enum_windows

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            modules = {
                'win32gui': mock_win32gui,
                'win32process': mock_win32process,
                'psutil': mock_psutil,
                'win32api': mock_win32api,
            }
            if name in modules:
                return modules[name]
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, '__import__', side_effect=mock_import):
            window = MainWindow.__new__(MainWindow)
            window.db = self.db
            window._monitor = MagicMock()

            windows = window._get_open_windows()

        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]['system_id'], 'chrome.exe')
        self.assertEqual(windows[0]['display_name'], 'Google Chrome')
        self.assertEqual(windows[0]['title'], 'Chrome Browser')

    def test_get_open_windows_excludes_excluded(self):
        """Исключённые приложения не попадают в список открытых окон."""
        from ui.main_window import MainWindow

        mock_win32gui = MagicMock()
        mock_win32process = MagicMock()
        mock_psutil = MagicMock()
        mock_win32api = MagicMock()

        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.GetWindowText.return_value = 'Calculator'
        mock_win32process.GetWindowThreadProcessId.return_value = (0, 9999)

        mock_process = MagicMock()
        mock_process.name.return_value = 'calculator.exe'
        mock_psutil.Process.return_value = mock_process

        mock_win32api.GetFileVersionInfo.side_effect = [
            [(0, 0)],
            'Calculator'
        ]

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            modules = {
                'win32gui': mock_win32gui,
                'win32process': mock_win32process,
                'psutil': mock_psutil,
                'win32api': mock_win32api,
            }
            if name in modules:
                return modules[name]
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, '__import__', side_effect=mock_import):
            window = MainWindow.__new__(MainWindow)
            window.db = self.db
            window._monitor = MagicMock()

            windows = window._get_open_windows()

        # calculator.exe в исключениях — его не должно быть
        self.assertEqual(len(windows), 0)

    # --- Вкладка «Отслеживаются» ---

    def test_add_track_from_open(self):
        """Добавление приложения для отслеживания."""
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window._monitor = MagicMock()
        window._refresh_all = MagicMock()

        window._add_track_from_open('notepad.exe', 'Блокнот')

        app = self.db.get_app_by_system_id('notepad.exe')
        self.assertIsNotNone(app)
        self.assertEqual(app['is_tracked'], 1)

    def test_remove_tracked(self):
        """Удаление приложения из отслеживания."""
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window._monitor = MagicMock()
        window._refresh_all = MagicMock()

        with patch('ui.main_window.QMessageBox.question', return_value=65536):  # QMessageBox.Yes
            window._remove_tracked('chrome.exe')

        app = self.db.get_app_by_system_id('chrome.exe')
        self.assertEqual(app['is_tracked'], 0)

    def test_remove_tracked_cancelled(self):
        """Отмена удаления не меняет статус."""
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window._monitor = MagicMock()
        window._refresh_all = MagicMock()

        with patch('ui.main_window.QMessageBox.question', return_value=65536):  # No
            window._remove_tracked('chrome.exe')

        app = self.db.get_app_by_system_id('chrome.exe')
        self.assertEqual(app['is_tracked'], 1)

    def test_add_limit_from_tracked(self):
        """Добавление лимита из отслеживаемых."""
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window._monitor = MagicMock()
        window._refresh_tracked_tab = MagicMock()

        # Мокаем диалог
        with patch('ui.main_window.AddLimitDialog') as mock_dialog:
            mock_instance = mock_dialog.return_value
            mock_instance.exec_.return_value = 1  # Accepted
            mock_instance.app_name = 'Spotify'
            mock_instance.limit_minutes = 30

            window._add_limit_from_tracked('Spotify')

        # Проверяем, что лимит создан
        limit = self.db.get_limit_by_system_id('spotify.exe')
        self.assertIsNotNone(limit)
        self.assertEqual(limit['limit_minutes'], 30)
        self.assertTrue(limit['enabled'])

    # --- Вкладка «Исключения» ---

    def test_exclude_from_table(self):
        """Исключение приложения."""
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window._monitor = MagicMock()
        window._refresh_all = MagicMock()

        window._exclude_from_table('notepad.exe', 'Блокнот')

        excluded = self.db.get_excluded_apps()
        self.assertTrue(any(e['system_id'] == 'notepad.exe' for e in excluded))

    def test_remove_excluded(self):
        """Удаление приложения из исключений."""
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window._monitor = MagicMock()
        window._refresh_all = MagicMock()

        with patch('ui.main_window.QMessageBox.question', return_value=65536):
            window._remove_excluded('calculator.exe')

        excluded = self.db.get_excluded_apps()
        self.assertFalse(any(e['system_id'] == 'calculator.exe' for e in excluded))

    def test_add_exclude_dialog(self):
        """Добавление исключения через диалог."""
        from ui.main_window import MainWindow

        # Создаём окно через __new__ и вручную устанавливаем нужные атрибуты
        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window._monitor = MagicMock()
        window._refresh_all = MagicMock()

        # Мокаем AddLimitDialog на уровне limit_dialog, чтобы __init__ не падал
        with patch('ui.dialogs.limit_dialog.AddLimitDialog') as mock_dialog_class:
            mock_instance = mock_dialog_class.return_value
            mock_instance.exec_.return_value = 1
            mock_instance.app_name = 'new_app.exe'

            window._add_exclude_dialog()

        excluded = self.db.get_excluded_apps()
        self.assertTrue(any(e['system_id'] == 'new_app.exe' for e in excluded))

    # --- Обновление вкладок ---

    def test_refresh_tracked_tab(self):
        """_refresh_tracked_tab заполняет таблицу данными из БД."""
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window._monitor = MagicMock()

        # Создаём мок для tracked_table
        window.tracked_table = MagicMock()

        window._refresh_tracked_tab()

        # Проверяем, что populate был вызван с данными
        window.tracked_table.populate.assert_called_once()
        args, _ = window.tracked_table.populate.call_args
        items, limits = args
        # Должны быть отслеживаемые приложения
        self.assertTrue(len(items) >= 2)
        # Лимиты должны быть проиндексированы по system_id
        self.assertIn('chrome.exe', limits)
        self.assertIn('code.exe', limits)

    def test_refresh_excluded_tab(self):
        """_refresh_excluded_tab заполняет таблицу исключений."""
        from ui.main_window import MainWindow
        from PyQt5.QtWidgets import QTableWidget

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window._monitor = MagicMock()
        window.excluded_table = QTableWidget()

        window._refresh_excluded_tab()

        self.assertGreaterEqual(window.excluded_table.rowCount(), 1)
        self.assertEqual(window.excluded_table.item(0, 0).text(), 'calculator.exe')

    # --- Продление лимита ---

    def test_extend_limit(self):
        """Продление лимита работает корректно."""
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window._extensions = {}

        # Первое продление
        result = window.extend_limit('test_app')
        self.assertTrue(result)
        self.assertEqual(window._extensions['test_app'], 5)

        # Второе продление
        result = window.extend_limit('test_app')
        self.assertTrue(result)
        self.assertEqual(window._extensions['test_app'], 10)

        # Третье — до максимума
        result = window.extend_limit('test_app')
        self.assertTrue(result)
        self.assertEqual(window._extensions['test_app'], 15)

        # Превышение максимума
        result = window.extend_limit('test_app')
        self.assertFalse(result)
        self.assertEqual(window._extensions['test_app'], 15)

    # --- Уведомления ---

    def test_show_limit_notification(self):
        """show_limit_notification вызывает notifier."""
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window.tray = MagicMock()
        window.tray.notifier = MagicMock()

        window.show_limit_notification('TestApp', 60)

        window.tray.notifier.show_limit_notification.assert_called_once_with('TestApp', 60)

    # --- Обновление времени ---

    def test_update_open_tab_time_for(self):
        """_update_open_tab_time_for корректно обновляет время."""
        from ui.main_window import MainWindow
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window.open_table = QTableWidget()
        window.open_table.setColumnCount(4)

        # Добавляем строку
        window.open_table.setRowCount(1)
        window.open_table.setItem(0, 0, QTableWidgetItem('chrome.exe'))
        window.open_table.setItem(0, 1, QTableWidgetItem('Chrome'))
        window.open_table.setItem(0, 2, QTableWidgetItem('Window'))
        window.open_table.setItem(0, 3, QTableWidgetItem('0:00:00'))

        window._update_open_tab_time_for('chrome.exe')

        # Chrome: 7200 сек = 2:00:00
        self.assertEqual(window.open_table.item(0, 3).text(), '2:00:00')

    def test_update_open_tab_time_for_exceeded_limit(self):
        """При превышении лимита строка окрашивается красным."""
        from ui.main_window import MainWindow
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
        from PyQt5.QtGui import QColor

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window.open_table = QTableWidget()
        window.open_table.setColumnCount(4)

        window.open_table.setRowCount(1)
        window.open_table.setItem(0, 0, QTableWidgetItem('chrome.exe'))
        window.open_table.setItem(0, 1, QTableWidgetItem('Chrome'))
        window.open_table.setItem(0, 2, QTableWidgetItem('Window'))
        window.open_table.setItem(0, 3, QTableWidgetItem('0:00:00'))

        window._update_open_tab_time_for('chrome.exe')

        # Проверяем красный фон (лимит 60 мин, использовано 120 мин)
        bg = window.open_table.item(0, 0).background().color()
        r, g, b, _ = bg.getRgb()
        self.assertGreater(r, g)
        self.assertGreater(r, b)

    # --- Активное приложение ---

    def test_get_active_system_id(self):
        """_get_active_system_id возвращает имя процесса активного окна."""
        from ui.main_window import MainWindow

        mock_win32gui = MagicMock()
        mock_win32process = MagicMock()
        mock_psutil = MagicMock()

        mock_win32gui.GetForegroundWindow.return_value = 12345
        mock_win32process.GetWindowThreadProcessId.return_value = (0, 6789)

        mock_process = MagicMock()
        mock_process.name.return_value = 'chrome.exe'
        mock_psutil.Process.return_value = mock_process

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            modules = {
                'win32gui': mock_win32gui,
                'win32process': mock_win32process,
                'psutil': mock_psutil,
            }
            if name in modules:
                return modules[name]
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, '__import__', side_effect=mock_import):
            window = MainWindow.__new__(MainWindow)
            result = window._get_active_system_id()

        self.assertEqual(result, 'chrome.exe')

    def test_get_active_system_id_no_window(self):
        """Если нет активного окна, возвращается None."""
        from ui.main_window import MainWindow

        mock_win32gui = MagicMock()
        mock_win32gui.GetForegroundWindow.return_value = 0

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'win32gui':
                return mock_win32gui
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, '__import__', side_effect=mock_import):
            window = MainWindow.__new__(MainWindow)
            result = window._get_active_system_id()

        self.assertIsNone(result)

    # --- Двойной клик ---

    def test_on_open_double_click(self):
        """Двойной клик переключает на вкладку отслеживаемых."""
        from ui.main_window import MainWindow
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QTabWidget

        window = MainWindow.__new__(MainWindow)
        window.db = self.db
        window.tabs = QTabWidget()
        window.tracked_table = MagicMock()
        window.tracked_table.rowCount.return_value = 1
        window.tracked_table.item.return_value = QTableWidgetItem('Google Chrome')

        window.open_table = QTableWidget()
        window.open_table.setColumnCount(4)
        window.open_table.setRowCount(1)
        window.open_table.setItem(0, 0, QTableWidgetItem('chrome.exe'))

        window._on_open_double_click(0, 0)

        self.assertEqual(window.tabs.currentIndex(), 1)
