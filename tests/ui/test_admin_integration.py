"""
Интеграционный тест для AdminUI — удалённого интерфейса администрирования.

Запускает реальный API-сервер (AppMonitorAPI) с тестовой БД,
создаёт AdminClient и проверяет все эндпоинты: статус, активность,
лимиты, настройки, приложения, исключения, авторизацию.
"""
import unittest
import threading
import time
import json
import asyncio
import os
import sys

from tests.conftest import create_test_db, cleanup_test_db


class TestAdminClientIntegration(unittest.TestCase):
    """Интеграционные тесты AdminClient с реальным API-сервером."""

    HOST = '127.0.0.1'
    PORT = 18765  # нестандартный порт, чтобы не мешать основному серверу
    BASE_URL = f'http://{HOST}:{PORT}'

    @classmethod
    def setUpClass(cls):
        """Запустить API-сервер в фоновом потоке."""
        cls.db, cls.db_path = create_test_db()

        # Импортируем после создания БД
        from api.server import AppMonitorAPI

        cls.api_server = AppMonitorAPI(cls.db, host=cls.HOST, port=cls.PORT)
        cls.api_server.start()
        # Ждём, пока сервер запустится
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        """Остановить сервер и очистить БД."""
        cls.api_server.stop()
        cleanup_test_db(cls.db, cls.db_path)

    def setUp(self):
        """Создать клиент для каждого теста."""
        from ui.admin_ui import AdminClient
        self.client = AdminClient(self.BASE_URL)

    # ── Статус ──────────────────────────────────────────────────────

    def test_get_status(self):
        """GET /api/status возвращает корректный статус."""
        status = self.client.get_status()
        self.assertIn('status', status)
        self.assertEqual(status['status'], 'ok')
        self.assertIn('uptime_seconds', status)
        self.assertIsInstance(status['uptime_seconds'], int)
        self.assertIn('monitored_apps', status)
        self.assertIsInstance(status['monitored_apps'], int)

    # ── Активность ──────────────────────────────────────────────────

    def test_get_today_activity(self):
        """GET /api/activity/today возвращает активность за сегодня."""
        activity = self.client.get_today_activity()
        self.assertIsInstance(activity, list)
        # В тестовых данных 4 приложения с активностью
        self.assertGreater(len(activity), 0)
        for item in activity:
            self.assertIn('app_name', item)
            self.assertIn('duration_seconds', item)
            self.assertIsInstance(item['duration_seconds'], int)

    def test_get_activity_by_date(self):
        """GET /api/activity/date/{date} возвращает активность за дату."""
        import datetime
        today = datetime.date.today().isoformat()
        activity = self.client.get_activity_by_date(today)
        self.assertIsInstance(activity, list)
        self.assertGreater(len(activity), 0)

    def test_get_activity_by_invalid_date(self):
        """GET /api/activity/date с несуществующей датой возвращает []."""
        activity = self.client.get_activity_by_date('2000-01-01')
        self.assertIsInstance(activity, list)
        self.assertEqual(len(activity), 0)

    # ── Авторизация ─────────────────────────────────────────────────

    def test_login_success(self):
        """POST /api/auth/login с верными данными возвращает токен."""
        result = self.client.login('admin', 'admin')
        self.assertTrue(result)
        self.assertIsNotNone(self.client._token)

    def test_login_wrong_password(self):
        """POST /api/auth/login с неверным паролем возвращает False."""
        result = self.client.login('admin', 'wrong_password')
        self.assertFalse(result)
        self.assertIsNone(self.client._token)

    def test_login_unknown_user(self):
        """POST /api/auth/login с неизвестным пользователем возвращает False."""
        result = self.client.login('unknown', 'password')
        self.assertFalse(result)

    # ── Лимиты ──────────────────────────────────────────────────────

    def test_get_limits(self):
        """GET /api/limits возвращает список лимитов."""
        limits = self.client.get_limits()
        self.assertIsInstance(limits, list)
        # В тестовых данных 2 лимита (chrome.exe: 60мин, code.exe: 120мин)
        self.assertGreaterEqual(len(limits), 2)
        for limit in limits:
            self.assertIn('system_id', limit)
            self.assertIn('limit_minutes', limit)
            self.assertIn('enabled', limit)

    def test_set_limit(self):
        """POST /api/limits создаёт новый лимит."""
        # Сначала логинимся
        self.client.login('admin', 'admin')
        result = self.client.set_limit('test_app.exe', 30, True, app_name='Test App')
        self.assertIsNotNone(result)

        # Проверяем, что лимит появился
        limits = self.client.get_limits()
        test_limits = [l for l in limits if l['system_id'] == 'test_app.exe']
        self.assertEqual(len(test_limits), 1)
        self.assertEqual(test_limits[0]['limit_minutes'], 30)
        self.assertTrue(test_limits[0]['enabled'])

    def test_set_limit_without_auth(self):
        """POST /api/limits без авторизации возвращает ошибку."""
        with self.assertRaises(Exception):
            self.client.set_limit('noauth.exe', 30, True)

    def test_delete_limit(self):
        """DELETE /api/limits/{system_id} удаляет лимит."""
        self.client.login('admin', 'admin')
        # Сначала создаём
        self.client.set_limit('delete_me.exe', 15, True)
        # Удаляем
        result = self.client.delete_limit('delete_me.exe')
        self.assertIsNotNone(result)

        # Проверяем, что лимит удалён
        limits = self.client.get_limits()
        deleted = [l for l in limits if l['system_id'] == 'delete_me.exe']
        self.assertEqual(len(deleted), 0)

    # ── Настройки ───────────────────────────────────────────────────

    def test_get_setting(self):
        """GET /api/settings/{key} возвращает настройку."""
        value = self.client.get_setting('test_key', 'default_val')
        self.assertEqual(value, 'default_val')

    def test_set_setting(self):
        """POST /api/settings сохраняет настройку."""
        self.client.login('admin', 'admin')
        self.client.set_setting('test_key', 'test_value')
        value = self.client.get_setting('test_key')
        self.assertEqual(value, 'test_value')

    def test_get_all_settings(self):
        """GET /api/settings возвращает все настройки."""
        settings = self.client.get_all_settings()
        self.assertIsInstance(settings, list)

    # ── Приложения ──────────────────────────────────────────────────

    def test_get_apps(self):
        """GET /api/apps возвращает список приложений."""
        apps = self.client.get_apps()
        self.assertIsInstance(apps, list)
        self.assertGreater(len(apps), 0)
        for app in apps:
            self.assertIn('app_name', app)
            self.assertIn('system_id', app)

    def test_get_tracked_apps(self):
        """GET /api/apps/tracked возвращает отслеживаемые приложения."""
        apps = self.client.get_tracked_apps()
        self.assertIsInstance(apps, list)
        for app in apps:
            self.assertTrue(app.get('is_tracked', False))

    def test_set_tracked(self):
        """POST /api/apps/tracked изменяет статус отслеживания."""
        self.client.login('admin', 'admin')
        # Отключаем отслеживание для chrome.exe
        self.client.set_tracked('chrome.exe', False)
        apps = self.client.get_tracked_apps()
        chrome = [a for a in apps if a['system_id'] == 'chrome.exe']
        self.assertEqual(len(chrome), 0)

        # Включаем обратно
        self.client.set_tracked('chrome.exe', True)
        apps = self.client.get_tracked_apps()
        chrome = [a for a in apps if a['system_id'] == 'chrome.exe']
        self.assertEqual(len(chrome), 1)

    # ── Исключения ──────────────────────────────────────────────────

    def test_get_excluded(self):
        """GET /api/excluded возвращает список исключений."""
        excluded = self.client.get_excluded()
        self.assertIsInstance(excluded, list)
        # В тестовых данных 1 исключение (calculator.exe)
        self.assertGreaterEqual(len(excluded), 1)

    def test_add_excluded(self):
        """POST /api/excluded добавляет исключение."""
        self.client.login('admin', 'admin')
        self.client.add_excluded('new_excluded.exe')
        excluded = self.client.get_excluded()
        new_excluded = [e for e in excluded if e['system_id'] == 'new_excluded.exe']
        self.assertEqual(len(new_excluded), 1)

    def test_remove_excluded(self):
        """DELETE /api/excluded/{system_id} удаляет исключение."""
        self.client.login('admin', 'admin')
        # Сначала добавляем
        self.client.add_excluded('temp_excluded.exe')
        # Удаляем
        self.client.remove_excluded('temp_excluded.exe')
        excluded = self.client.get_excluded()
        temp = [e for e in excluded if e['system_id'] == 'temp_excluded.exe']
        self.assertEqual(len(temp), 0)

    # ── Активность за период ────────────────────────────────────────

    def test_get_activity_period(self):
        """POST /api/activity/period возвращает активность за период."""
        import datetime
        today = datetime.date.today().isoformat()
        result = self.client.get_activity_period(today, today)
        self.assertIn('total_seconds', result)
        self.assertIn('apps', result)
        self.assertIsInstance(result['apps'], list)
        self.assertGreater(result['total_seconds'], 0)

    def test_get_tracked_activity_period(self):
        """POST /api/activity/tracked/period возвращает активность отслеживаемых."""
        import datetime
        today = datetime.date.today().isoformat()
        result = self.client.get_tracked_activity_period(today, today)
        self.assertIn('total_seconds', result)
        self.assertIn('apps', result)

    def test_get_app_activity(self):
        """GET /api/activity/app/{system_id} возвращает активность приложения."""
        import datetime
        today = datetime.date.today().isoformat()
        activity = self.client.get_app_activity('chrome.exe', today, today)
        self.assertIsInstance(activity, list)
        self.assertGreater(len(activity), 0)

    # ── WebSocket ───────────────────────────────────────────────────

    def test_websocket_connect(self):
        """WebSocket /ws подключается и отвечает на ping."""
        import asyncio
        import websockets
        import ssl

        async def _test():
            ws_url = self.BASE_URL.replace('http://', 'ws://') + '/ws'
            async with websockets.connect(ws_url) as ws:
                # Отправляем ping
                await ws.send(json.dumps({'action': 'ping'}))
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                msg = json.loads(response)
                self.assertEqual(msg['type'], 'pong')

        asyncio.run(_test())

    def test_websocket_get_today(self):
        """WebSocket /ws возвращает активность по запросу get_today."""
        import asyncio
        import websockets

        async def _test():
            ws_url = self.BASE_URL.replace('http://', 'ws://') + '/ws'
            async with websockets.connect(ws_url) as ws:
                await ws.send(json.dumps({'action': 'get_today'}))
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                msg = json.loads(response)
                self.assertEqual(msg['type'], 'activity')
                self.assertIn('data', msg)
                self.assertIsInstance(msg['data'], list)

        asyncio.run(_test())

    def test_websocket_get_limits(self):
        """WebSocket /ws возвращает лимиты по запросу get_limits."""
        import asyncio
        import websockets

        async def _test():
            ws_url = self.BASE_URL.replace('http://', 'ws://') + '/ws'
            async with websockets.connect(ws_url) as ws:
                await ws.send(json.dumps({'action': 'get_limits'}))
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                msg = json.loads(response)
                self.assertEqual(msg['type'], 'limits')
                self.assertIn('data', msg)
                self.assertIsInstance(msg['data'], list)

        asyncio.run(_test())


class TestAdminClientEdgeCases(unittest.TestCase):
    """Тесты граничных случаев AdminClient."""

    def test_invalid_url(self):
        """AdminClient с неверным URL выбрасывает исключение."""
        from ui.admin_ui import AdminClient
        client = AdminClient('http://localhost:1')
        with self.assertRaises(Exception):
            client.get_status()

    def test_connection_refused(self):
        """AdminClient с несуществующим сервером выбрасывает исключение."""
        from ui.admin_ui import AdminClient
        client = AdminClient('http://127.0.0.1:1')
        with self.assertRaises(Exception):
            client.get_status()

    def test_base_url_trailing_slash(self):
        """AdminClient обрезает завершающий слеш в URL."""
        from ui.admin_ui import AdminClient
        client = AdminClient('http://localhost:8765/')
        self.assertEqual(client.base_url, 'http://localhost:8765')

    def test_ws_url_conversion(self):
        """AdminClient корректно конвертирует http в ws."""
        from ui.admin_ui import AdminClient
        client = AdminClient('http://localhost:8765')
        self.assertEqual(client.ws_url, 'ws://localhost:8765')

        client_https = AdminClient('https://localhost:8765')
        self.assertEqual(client_https.ws_url, 'wss://localhost:8765')


if __name__ == '__main__':
    unittest.main()
