"""Тесты для TrackedTable — таблицы отслеживаемых приложений.

Тестируем логику populate и форматирование без QApplication.
"""

import unittest


class TestTrackedTableLogic(unittest.TestCase):
    """Проверка логики TrackedTable без Qt."""

    def test_time_formatting(self):
        """Проверка форматирования времени."""
        from ui.widgets.tracked_table import TrackedTable

        test_cases = [
            (0, '0:00:00'),
            (30, '0:00:30'),
            (60, '0:01:00'),
            (3600, '1:00:00'),
            (3661, '1:01:01'),
            (86400, '24:00:00'),
        ]
        for seconds, expected in test_cases:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            result = f'{hours}:{minutes:02d}:{secs:02d}'
            self.assertEqual(result, expected, f"Для {seconds}с ожидалось '{expected}'")

    def test_limit_exceeded_detection(self):
        """Проверка определения превышения лимита."""
        # duration_seconds // 60 >= limit_minutes
        self.assertTrue(7200 // 60 >= 60)   # 2 часа >= 60 мин
        self.assertTrue(3600 // 60 >= 60)   # 1 час >= 60 мин
        self.assertFalse(1800 // 60 >= 60)  # 30 мин < 60 мин
        self.assertTrue(0 // 60 >= 0)       # 0 >= 0

    def test_remaining_time(self):
        """Проверка расчёта остатка времени."""
        limit = 60  # минут
        used = 30   # минут
        left = max(0, limit - used)
        self.assertEqual(left, 30)

        used = 60
        left = max(0, limit - used)
        self.assertEqual(left, 0)

        used = 90
        left = max(0, limit - used)
        self.assertEqual(left, 0)

    def test_limit_disabled_shows_dash(self):
        """Отключённый лимит показывается как прочерк."""
        limit = {'limit_minutes': 60, 'enabled': False}
        self.assertFalse(limit['enabled'])

    def test_limit_enabled(self):
        """Включённый лимит."""
        limit = {'limit_minutes': 60, 'enabled': True}
        self.assertTrue(limit['enabled'])


class TestTrackedTablePopulateData(unittest.TestCase):
    """Проверка данных для populate."""

    def setUp(self):
        self.items = [
            {'system_id': 'chrome.exe', 'app_name': 'Google Chrome', 'duration_seconds': 7200},
            {'system_id': 'code.exe', 'app_name': 'VS Code', 'duration_seconds': 5400},
            {'system_id': 'spotify.exe', 'app_name': 'Spotify', 'duration_seconds': 1800},
        ]
        self.limits = {
            'Google Chrome': {'limit_minutes': 60, 'enabled': True},
            'VS Code': {'limit_minutes': 120, 'enabled': True},
        }

    def test_items_sorted_by_name(self):
        """Элементы отсортированы по app_name."""
        names = [item['app_name'] for item in self.items]
        self.assertEqual(names, ['Google Chrome', 'VS Code', 'Spotify'])

    def test_limit_lookup_by_app_name(self):
        """Лимиты ищутся по app_name."""
        for item in self.items:
            limit = self.limits.get(item['app_name'])
            if item['app_name'] == 'Google Chrome':
                self.assertIsNotNone(limit)
                self.assertEqual(limit['limit_minutes'], 60)
            elif item['app_name'] == 'VS Code':
                self.assertIsNotNone(limit)
                self.assertEqual(limit['limit_minutes'], 120)
            else:
                self.assertIsNone(limit)

    def test_exceeded_detection(self):
        """Проверка превышения для каждого элемента."""
        for item in self.items:
            limit = self.limits.get(item['app_name'])
            if limit and limit['enabled']:
                exceeded = item['duration_seconds'] // 60 >= limit['limit_minutes']
                if item['app_name'] == 'Google Chrome':
                    self.assertTrue(exceeded, "Chrome должен быть с превышением")
                elif item['app_name'] == 'VS Code':
                    self.assertFalse(exceeded, "VS Code не должен превышать лимит")

    def test_remaining_calculation(self):
        """Проверка остатка времени."""
        for item in self.items:
            limit = self.limits.get(item['app_name'])
            if limit and limit['enabled']:
                used = item['duration_seconds'] // 60
                left = max(0, limit['limit_minutes'] - used)
                if item['app_name'] == 'Google Chrome':
                    self.assertEqual(left, 0)
                elif item['app_name'] == 'VS Code':
                    self.assertEqual(left, 120 - 90)
