import sqlite3
import os
import datetime
from core.logger import setup_logger

logger = setup_logger('core.database')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'app_monitor.db')


class Database:
    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        logger.info(f'База данных: {db_path}')
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL,
                    window_title TEXT,
                    date TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL DEFAULT 0,
                    last_seen TEXT
                );
                CREATE TABLE IF NOT EXISTS limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL UNIQUE,
                    limit_minutes INTEGER NOT NULL DEFAULT 60,
                    enabled INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_activity_date ON activity(date);
                CREATE INDEX IF NOT EXISTS idx_activity_app ON activity(app_name);
            """)
            conn.commit()
            logger.debug('Таблицы БД инициализированы')
        except Exception as e:
            logger.error(f'Ошибка инициализации БД: {e}')
        finally:
            conn.close()

    def update_activity(self, app_name: str, duration_seconds: int):
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                'UPDATE activity SET duration_seconds = duration_seconds + ?, last_seen = ? '
                'WHERE app_name = ? AND date = ?',
                (duration_seconds, datetime.datetime.now().isoformat(), app_name, today)
            )
            conn.commit()
            logger.debug(f'Активность обновлена: {app_name} +{duration_seconds}с')
        finally:
            conn.close()

    def get_or_create_today_activity(self, app_name: str, window_title: str = "") -> dict:
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT * FROM activity WHERE app_name = ? AND date = ?',
                (app_name, today)
            ).fetchone()
            if row:
                if window_title:
                    conn.execute(
                        'UPDATE activity SET window_title = ?, last_seen = ? WHERE id = ?',
                        (window_title, datetime.datetime.now().isoformat(), row['id'])
                    )
                    conn.commit()
                return dict(row)
            conn.execute(
                'INSERT INTO activity (app_name, window_title, date, last_seen) VALUES (?, ?, ?, ?)',
                (app_name, window_title, today, datetime.datetime.now().isoformat())
            )
            conn.commit()
            logger.debug(f'Новая запись активности: {app_name}')
            row = conn.execute(
                'SELECT * FROM activity WHERE app_name = ? AND date = ?',
                (app_name, today)
            ).fetchone()
            return dict(row) if row else {'app_name': app_name, 'duration_seconds': 0}
        finally:
            conn.close()

    def get_today_activity(self) -> list:
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT * FROM activity WHERE date = ? ORDER BY duration_seconds DESC',
                (today,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_limit(self, app_name: str):
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT * FROM limits WHERE app_name = ?', (app_name,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_limits(self) -> list:
        conn = self._get_connection()
        try:
            rows = conn.execute('SELECT * FROM limits ORDER BY app_name').fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def set_limit(self, app_name: str, limit_minutes: int, enabled: bool = True):
        conn = self._get_connection()
        try:
            conn.execute(
                'INSERT INTO limits (app_name, limit_minutes, enabled) VALUES (?, ?, ?) '
                'ON CONFLICT(app_name) DO UPDATE SET limit_minutes = ?, enabled = ?',
                (app_name, limit_minutes, int(enabled), limit_minutes, int(enabled))
            )
            conn.commit()
            logger.debug(f'Лимит сохранён: {app_name} = {limit_minutes} мин (enabled={enabled})')
        finally:
            conn.close()

    def delete_limit(self, app_name: str):
        conn = self._get_connection()
        try:
            conn.execute('DELETE FROM limits WHERE app_name = ?', (app_name,))
            conn.commit()
            logger.debug(f'Лимит удалён: {app_name}')
        finally:
            conn.close()

    def get_setting(self, key: str, default: str = "") -> str:
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT value FROM settings WHERE key = ?', (key,)
            ).fetchone()
            return row['value'] if row else default
        finally:
            conn.close()

    def set_setting(self, key: str, value: str):
        conn = self._get_connection()
        try:
            conn.execute(
                'INSERT INTO settings (key, value) VALUES (?, ?) '
                'ON CONFLICT(key) DO UPDATE SET value = ?',
                (key, value, value)
            )
            conn.commit()
            logger.debug(f'Настройка сохранена: {key} = {value}')
        finally:
            conn.close()

    def reset_today(self):
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            conn.execute('DELETE FROM activity WHERE date = ?', (today,))
            conn.commit()
            logger.info(f'Активность за {today} сброшена')
        finally:
            conn.close()
