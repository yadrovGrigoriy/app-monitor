"""Тесты для StatsDialog — диалога статистики.

Тестируем бизнес-логику без QApplication.
"""

import unittest
from unittest.mock import MagicMock, patch
import datetime

from tests.conftest import create_test_db, cleanup_test_db


class TestStatsDialogLogic(unittest.TestCase):
    """Проверка логики StatsDialog."""

    def setUp(self):
        self.db, self.db_path = create_test_db()

    def tearDown(self):
        cleanup_test_db(self.db, self.db_path)

    def test_get_date_range_day(self):
        """get_date_range для 'day' возвращает один день."""
        from ui.dialogs.stats_dialog import StatsDialog

        dialog = StatsDialog.__new__(StatsDialog)
        dialog.db = self.db
        dialog.date_toolbar = MagicMock()
        dialog.date_toolbar.current_period.return_value = 'day'
        dialog.date_toolbar.selected_date.return_value = MagicMock()
        dialog.date_toolbar.selected_date.return_value.year.return_value = 2024
        dialog.date_toolbar.selected_date.return_value.month.return_value = 6
        dialog.date_toolbar.selected_date.return_value.day.return_value = 15

        start, end = dialog._get_date_range()

        self.assertEqual(start, '2024-06-15')
        self.assertEqual(end, '2024-06-15')

    def test_get_date_range_week(self):
        """get_date_range для 'week' возвращает неделю."""
        from ui.dialogs.stats_dialog import StatsDialog

        dialog = StatsDialog.__new__(StatsDialog)
        dialog.db = self.db
        dialog.date_toolbar = MagicMock()
        dialog.date_toolbar.current_period.return_value = 'week'
        dialog.date_toolbar.selected_date.return_value = MagicMock()
        dialog.date_toolbar.selected_date.return_value.year.return_value = 2024
        dialog.date_toolbar.selected_date.return_value.month.return_value = 6
        dialog.date_toolbar.selected_date.return_value.day.return_value = 19  # Wednesday
        dialog.date_toolbar.selected_date.return_value.weekday.return_value = 2  # Wednesday

        start, end = dialog._get_date_range()

        # Неделя с понедельника (17 июня) по воскресенье (23 июня)
        self.assertEqual(start, '2024-06-17')
        self.assertEqual(end, '2024-06-23')

    def test_get_date_range_month(self):
        """get_date_range для 'month' возвращает месяц."""
        from ui.dialogs.stats_dialog import StatsDialog

        dialog = StatsDialog.__new__(StatsDialog)
        dialog.db = self.db
        dialog.date_toolbar = MagicMock()
        dialog.date_toolbar.current_period.return_value = 'month'
        dialog.date_toolbar.selected_date.return_value = MagicMock()
        dialog.date_toolbar.selected_date.return_value.year.return_value = 2024
        dialog.date_toolbar.selected_date.return_value.month.return_value = 6
        dialog.date_toolbar.selected_date.return_value.day.return_value = 15

        start, end = dialog._get_date_range()

        self.assertEqual(start, '2024-06-01')
        self.assertEqual(end, '2024-06-30')

    def test_get_date_range_year(self):
        """get_date_range для 'year' возвращает год."""
        from ui.dialogs.stats_dialog import StatsDialog

        dialog = StatsDialog.__new__(StatsDialog)
        dialog.db = self.db
        dialog.date_toolbar = MagicMock()
        dialog.date_toolbar.current_period.return_value = 'year'
        dialog.date_toolbar.selected_date.return_value = MagicMock()
        dialog.date_toolbar.selected_date.return_value.year.return_value = 2024
        dialog.date_toolbar.selected_date.return_value.month.return_value = 6
        dialog.date_toolbar.selected_date.return_value.day.return_value = 15

        start, end = dialog._get_date_range()

        self.assertEqual(start, '2024-01-01')
        self.assertEqual(end, '2024-12-31')

    def test_get_date_range_month_december(self):
        """Декабрь — особый случай для месяца."""
        from ui.dialogs.stats_dialog import StatsDialog

        dialog = StatsDialog.__new__(StatsDialog)
        dialog.db = self.db
        dialog.date_toolbar = MagicMock()
        dialog.date_toolbar.current_period.return_value = 'month'
        dialog.date_toolbar.selected_date.return_value = MagicMock()
        dialog.date_toolbar.selected_date.return_value.year.return_value = 2024
        dialog.date_toolbar.selected_date.return_value.month.return_value = 12
        dialog.date_toolbar.selected_date.return_value.day.return_value = 25

        start, end = dialog._get_date_range()

        self.assertEqual(start, '2024-12-01')
        self.assertEqual(end, '2024-12-31')

    def test_get_daily_data(self):
        """_get_daily_data возвращает активность за период."""
        from ui.dialogs.stats_dialog import StatsDialog

        dialog = StatsDialog.__new__(StatsDialog)
        dialog.db = self.db

        today = datetime.date.today().isoformat()
        data = dialog._get_daily_data(today, today)

        self.assertGreater(len(data), 0)
        # Проверяем структуру данных
        for row in data:
            self.assertIn('app_name', row)
            self.assertIn('duration_seconds', row)

    def test_get_daily_data_empty_period(self):
        """_get_daily_data для периода без данных."""
        from ui.dialogs.stats_dialog import StatsDialog

        dialog = StatsDialog.__new__(StatsDialog)
        dialog.db = self.db

        data = dialog._get_daily_data('2020-01-01', '2020-01-01')

        self.assertEqual(len(data), 0)

    def test_tracked_only_filter(self):
        """Проверка фильтра 'только отслеживаемые'."""
        from ui.dialogs.stats_dialog import StatsDialog

        dialog = StatsDialog.__new__(StatsDialog)
        dialog.db = self.db
        dialog.tracked_only_check = MagicMock()
        dialog.tracked_only_check.isChecked.return_value = True
        dialog.date_toolbar = MagicMock()
        dialog.date_toolbar.current_period.return_value = 'day'
        dialog.date_toolbar.selected_date.return_value = MagicMock()
        dialog.date_toolbar.selected_date.return_value.year.return_value = 2024
        dialog.date_toolbar.selected_date.return_value.month.return_value = 6
        dialog.date_toolbar.selected_date.return_value.day.return_value = 15

        # Мокаем _build_chart, чтобы не рисовать
        dialog._build_chart = MagicMock()

        # Проверяем, что при tracked_only=True вызывается get_tracked_activity_for_period
        with patch.object(dialog.db, 'get_tracked_activity_for_period', return_value=[]) as mock_tracked:
            with patch.object(dialog.db, 'get_activity_for_period', return_value=[]) as mock_all:
                dialog._build_chart()

        mock_tracked.assert_called_once()
        mock_all.assert_not_called()

    def test_all_apps_filter(self):
        """Без фильтра показываются все приложения."""
        from ui.dialogs.stats_dialog import StatsDialog

        dialog = StatsDialog.__new__(StatsDialog)
        dialog.db = self.db
        dialog.tracked_only_check = MagicMock()
        dialog.tracked_only_check.isChecked.return_value = False
        dialog.date_toolbar = MagicMock()
        dialog.date_toolbar.current_period.return_value = 'day'
        dialog.date_toolbar.selected_date.return_value = MagicMock()
        dialog.date_toolbar.selected_date.return_value.year.return_value = 2024
        dialog.date_toolbar.selected_date.return_value.month.return_value = 6
        dialog.date_toolbar.selected_date.return_value.day.return_value = 15

        dialog._build_chart = MagicMock()

        with patch.object(dialog.db, 'get_activity_for_period', return_value=[]) as mock_all:
            with patch.object(dialog.db, 'get_tracked_activity_for_period', return_value=[]) as mock_tracked:
                dialog._build_chart()

        mock_all.assert_called_once()
        mock_tracked.assert_not_called()
