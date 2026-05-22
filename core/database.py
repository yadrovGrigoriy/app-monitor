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
                    system_id TEXT,
                    window_title TEXT,
                    date TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL DEFAULT 0,
                    last_seen TEXT
                );
                CREATE TABLE IF NOT EXISTS limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL UNIQUE,
                    system_id TEXT,
                    limit_minutes INTEGER NOT NULL DEFAULT 60,
                    enabled INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS excluded_apps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system_id TEXT NOT NULL UNIQUE,
                    display_name TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_activity_date ON activity(date);
                CREATE INDEX IF NOT EXISTS idx_activity_app ON activity(app_name);
            """)
            conn.commit()
            logger.debug('Таблицы БД инициализированы')
            # Миграции
            self._migrate_add_column(conn, 'activity', 'system_id', 'TEXT')
            self._migrate_add_column(conn, 'limits', 'system_id', 'TEXT')
            self._migrate_add_column(conn, 'activity', 'is_tracked', 'INTEGER NOT NULL DEFAULT 0')
            # Миграция: для существующих записей, у которых есть лимит, проставляем is_tracked=1
            try:
                conn.execute(
                    'UPDATE activity SET is_tracked = 1 '
                    'WHERE is_tracked = 0 AND app_name IN (SELECT app_name FROM limits)'
                )
                conn.commit()
            except sqlite3.OperationalError:
                pass
        except Exception as e:
            logger.error(f'Ошибка инициализации БД: {e}')
        finally:
            conn.close()

    @staticmethod
    def _migrate_add_column(conn: sqlite3.Connection, table: str, column: str, col_def: str):
        """Добавить колонку в таблицу, если её нет."""
        try:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_def}')
            conn.commit()
            logger.info(f'Миграция: добавлена колонка {column} в {table}')
        except sqlite3.OperationalError:
            pass

    def close(self):
        """Закрыть соединение с БД (заглушка, т.к. соединения создаются на лету)."""
        logger.debug('Database.close() вызван')
        pass

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

    def update_activity_by_system_id(self, system_id: str, duration_seconds: int):
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                'UPDATE activity SET duration_seconds = duration_seconds + ?, last_seen = ? '
                'WHERE LOWER(system_id) = ? AND date = ?',
                (duration_seconds, datetime.datetime.now().isoformat(), system_id.lower(), today)
            )
            conn.commit()
            logger.debug(f'Активность обновлена по system_id: {system_id} +{duration_seconds}с')
        finally:
            conn.close()

    def tick_activity(self, app_name: str, window_title: str, system_id: str):
        """Тик монитора: создать/обновить запись и прибавить 1с в одном соединении."""
        today = datetime.date.today().isoformat()
        now_iso = datetime.datetime.now().isoformat()
        system_id = system_id.lower()
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT id FROM activity WHERE LOWER(system_id) = ? AND date = ?',
                (system_id, today)
            ).fetchone()
            if row:
                conn.execute(
                    'UPDATE activity SET duration_seconds = duration_seconds + 1, '
                    'window_title = ?, last_seen = ? WHERE id = ?',
                    (window_title, now_iso, row['id'])
                )
            else:
                conn.execute(
                    'INSERT INTO activity (app_name, system_id, window_title, date, last_seen, is_tracked) '
                    'VALUES (?, ?, ?, ?, ?, 0)',
                    (app_name, system_id, window_title, today, now_iso)
                )
            conn.commit()
        finally:
            conn.close()

    def get_or_create_today_activity(self, app_name: str, window_title: str = "", system_id: str = "") -> dict:
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
                'INSERT INTO activity (app_name, system_id, window_title, date, last_seen, is_tracked) '
                'VALUES (?, ?, ?, ?, ?, 0)',
                (app_name, system_id.lower(), window_title, today, datetime.datetime.now().isoformat())
            )
            conn.commit()
            logger.debug(f'Новая запись активности: {app_name} (system_id={system_id})')
            row = conn.execute(
                'SELECT * FROM activity WHERE app_name = ? AND date = ?',
                (app_name, today)
            ).fetchone()
            return dict(row) if row else {'app_name': app_name, 'duration_seconds': 0}
        finally:
            conn.close()

    def get_or_create_today_activity_by_system_id(self, system_id: str) -> dict:
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT * FROM activity WHERE LOWER(system_id) = ? AND date = ?',
                (system_id.lower(), today)
            ).fetchone()
            if row:
                return dict(row)
            return {'system_id': system_id, 'duration_seconds': 0}
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

    def get_activity_for_period(self, start_date: str, end_date: str) -> list:
        """Вернуть агрегированную активность за период (сумма duration_seconds по приложениям)."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT app_name, MAX(window_title) as window_title, '
                'SUM(duration_seconds) as duration_seconds '
                'FROM activity WHERE date >= ? AND date <= ? '
                'GROUP BY app_name ORDER BY duration_seconds DESC',
                (start_date, end_date)
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

    def get_limit_by_system_id(self, system_id: str):
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT * FROM limits WHERE LOWER(system_id) = ?', (system_id.lower(),)
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

    def set_limit(self, app_name: str, limit_minutes: int, enabled: bool = True, system_id: str = ""):
        conn = self._get_connection()
        try:
            conn.execute(
                'INSERT INTO limits (app_name, system_id, limit_minutes, enabled) VALUES (?, ?, ?, ?) '
                'ON CONFLICT(app_name) DO UPDATE SET limit_minutes = ?, enabled = ?',
                (app_name, system_id.lower(), limit_minutes, int(enabled), limit_minutes, int(enabled))
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

    # ─── Отслеживание ──────────────────────────────────────────────

    def mark_as_tracked(self, app_name: str, system_id: str = ""):
        """Пометить приложение как отслеживаемое."""
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                'UPDATE activity SET is_tracked = 1 WHERE app_name = ? AND date = ?',
                (app_name, today)
            )
            if conn.total_changes == 0:
                conn.execute(
                    'INSERT INTO activity (app_name, system_id, date, last_seen, is_tracked) '
                    'VALUES (?, ?, ?, ?, 1)',
                    (app_name, system_id.lower(), today, datetime.datetime.now().isoformat())
                )
            conn.commit()
            logger.debug(f'Приложение помечено как отслеживаемое: {app_name}')
        finally:
            conn.close()

    def mark_as_untracked(self, system_id: str):
        """Убрать пометку отслеживания у приложения."""
        conn = self._get_connection()
        try:
            conn.execute(
                'UPDATE activity SET is_tracked = 0 WHERE LOWER(system_id) = ?',
                (system_id.lower(),)
            )
            conn.commit()
            logger.debug(f'Приложение помечено как неотслеживаемое: {system_id}')
        finally:
            conn.close()

    def get_tracked_activity(self, date_iso: str) -> list:
        """Вернуть только отслеживаемые приложения за дату."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT system_id, app_name, duration_seconds FROM activity '
                'WHERE date = ? AND is_tracked = 1 '
                'AND system_id IS NOT NULL AND system_id != \'\' '
                'ORDER BY app_name',
                (date_iso,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ─── Исключения ────────────────────────────────────────────────

    def get_excluded_apps(self) -> list:
        """Вернуть список исключённых приложений."""
        conn = self._get_connection()
        try:
            rows = conn.execute('SELECT * FROM excluded_apps ORDER BY system_id').fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def add_excluded_app(self, system_id: str, display_name: str = ""):
        """Добавить приложение в список исключений и удалить всю его активность."""
        system_id = system_id.lower()
        conn = self._get_connection()
        try:
            conn.execute(
                'INSERT OR IGNORE INTO excluded_apps (system_id, display_name) VALUES (?, ?)',
                (system_id, display_name)
            )
            conn.execute(
                'DELETE FROM activity WHERE LOWER(system_id) = ?',
                (system_id,)
            )
            conn.commit()
            logger.debug(f'Приложение добавлено в исключения: {system_id} ({display_name})')
        finally:
            conn.close()

    def remove_excluded_app(self, system_id: str):
        """Удалить приложение из списка исключений."""
        conn = self._get_connection()
        try:
            conn.execute('DELETE FROM excluded_apps WHERE LOWER(system_id) = ?', (system_id.lower(),))
            conn.commit()
            logger.debug(f'Приложение удалено из исключений: {system_id}')
        finally:
            conn.close()

    def is_app_excluded(self, system_id: str) -> bool:
        """Проверить, исключено ли приложение из отслеживания."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT 1 FROM excluded_apps WHERE LOWER(system_id) = ?', (system_id.lower(),)
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def remove_old_activity(self, date_iso: str, active_apps: set):
        """Удалить записи активности за дату, которых нет в active_apps."""
        conn = self._get_connection()
        try:
            deleted = conn.execute(
                'DELETE FROM activity WHERE date = ? AND app_name NOT IN ({})'.format(
                    ','.join('?' * len(active_apps))
                ),
                (date_iso, *active_apps)
            ).rowcount
            conn.commit()
            if deleted:
                logger.debug(f'Удалено {deleted} устаревших записей активности за {date_iso}')
        finally:
            conn.close()

    def close(self):
        """Закрыть соединение с БД (заглушка, т.к. соединения создаются на лету)."""
        logger.debug('Database.close() вызван')
        pass

    def get_setting(self, key: str, default: str = "") -> str:
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT value FROM settings WHERE key = ?', (key,)
            ).fetchone()
            return row['value'] if row else default
        finally:
            conn.close()

    def close(self):
        """Закрыть соединение с БД (заглушка, т.к. соединения создаются на лету)."""
        logger.debug('Database.close() вызван')
        pass

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

    def close(self):
        """Закрыть соединение с БД (заглушка, т.к. соединения создаются на лету)."""
        logger.debug('Database.close() вызван')
        pass

    def reset_today(self):
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            conn.execute('DELETE FROM activity WHERE date = ?', (today,))
            conn.commit()
            logger.info(f'Активность за {today} сброшена')
        finally:
            conn.close()

    def close(self):
        """Закрыть соединение с БД (заглушка, т.к. соединения создаются на лету)."""
        logger.debug('Database.close() вызван')
        pass

    # ─── Администраторы ────────────────────────────────────────────

    def add_admin(self, username: str, password_hash: str):
        conn = self._get_connection()
        try:
            conn.execute(
                'INSERT OR IGNORE INTO admins (username, password_hash) VALUES (?, ?)',
                (username, password_hash)
            )
            conn.commit()
            logger.debug(f'Администратор добавлен: {username}')
        finally:
            conn.close()

    def close(self):
        """Закрыть соединение с БД (заглушка, т.к. соединения создаются на лету)."""
        logger.debug('Database.close() вызван')
        pass

    def get_admin(self, username: str) -> dict | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT * FROM admins WHERE username = ?', (username,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def close(self):
        """Закрыть соединение с БД (заглушка, т.к. соединения создаются на лету)."""
        logger.debug('Database.close() вызван')
        pass

    def admin_exists(self) -> bool:
        conn = self._get_connection()
        try:
            row = conn.execute('SELECT 1 FROM admins LIMIT 1').fetchone()
            return row is not None
        finally:
            conn.close()

    def close(self):
        """Закрыть соединение с БД (заглушка, т.к. соединения создаются на лету)."""
        logger.debug('Database.close() вызван')
        pass
