"""Фикстуры для UI-тестов AppMonitor.

Используем unittest + unittest.mock, так как PyQt5 не может создать QApplication
в терминальном окружении без GUI-дисплея.
"""

import os
import sys
import tempfile
import datetime
from pathlib import Path

# Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Отключаем логи в тестах
os.environ['APPMONITOR_TESTING'] = '1'


def create_test_db():
    """Создать временную БД с тестовыми данными."""
    from core.database import Database

    tmpfile = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp_path = tmpfile.name
    tmpfile.close()

    db = Database(db_path=tmp_path)
    _seed_test_data(db)
    return db, tmp_path


def _seed_test_data(db):
    """Наполнить БД тестовыми данными."""
    conn = db._get_connection()
    try:
        apps_data = [
            ('chrome.exe', 'Google Chrome'),
            ('code.exe', 'Visual Studio Code'),
            ('spotify.exe', 'Spotify'),
            ('notepad.exe', 'Блокнот'),
        ]
        for sys_id, name in apps_data:
            conn.execute(
                'INSERT OR IGNORE INTO apps (app_name, system_id, is_tracked) VALUES (?, ?, ?)',
                (name, sys_id, 1 if sys_id in ('chrome.exe', 'code.exe') else 0)
            )

        today = datetime.date.today().isoformat()
        app_rows = conn.execute('SELECT id, system_id FROM apps').fetchall()
        for app in app_rows:
            sys_id = app['system_id']
            seconds = {
                'chrome.exe': 7200,
                'code.exe': 5400,
                'spotify.exe': 1800,
                'notepad.exe': 300,
            }.get(sys_id, 0)
            if seconds > 0:
                conn.execute(
                    'INSERT OR IGNORE INTO daily_activity (app_id, date, total_seconds) VALUES (?, ?, ?)',
                    (app['id'], today, seconds)
                )

        chrome_app = conn.execute(
            "SELECT id FROM apps WHERE system_id = 'chrome.exe'"
        ).fetchone()
        if chrome_app:
            conn.execute(
                'INSERT OR IGNORE INTO limits (app_id, limit_minutes, enabled) VALUES (?, ?, ?)',
                (chrome_app['id'], 60, 1)
            )

        code_app = conn.execute(
            "SELECT id FROM apps WHERE system_id = 'code.exe'"
        ).fetchone()
        if code_app:
            conn.execute(
                'INSERT OR IGNORE INTO limits (app_id, limit_minutes, enabled) VALUES (?, ?, ?)',
                (code_app['id'], 120, 1)
            )

        conn.execute(
            "INSERT OR IGNORE INTO excluded_apps (system_id, display_name) VALUES (?, ?)",
            ('calculator.exe', 'Калькулятор')
        )

        conn.commit()
    finally:
        conn.close()


def cleanup_test_db(db, db_path):
    """Очистить временную БД."""
    db.close()
    try:
        os.unlink(db_path)
    except PermissionError:
        pass
