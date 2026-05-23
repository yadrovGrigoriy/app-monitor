import sqlite3
import os
import datetime
from core.logger import setup_logger

logger = setup_logger('core.database')

# Приоритет: папка рядом с exe (для разработки), иначе %APPDATA%
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.access(_base, os.W_OK):
    _base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AppMonitor')

DB_PATH = os.path.join(_base, 'data', 'app_monitor.db')


class Database:
    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        logger.info(f'База данных: {db_path}')
        self._init_db()
        self._ensure_default_admin()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            statements = [
                'CREATE TABLE IF NOT EXISTS apps ('
                '  id INTEGER PRIMARY KEY AUTOINCREMENT,'
                '  app_name TEXT NOT NULL,'
                '  system_id TEXT NOT NULL UNIQUE,'
                '  is_tracked INTEGER NOT NULL DEFAULT 0)',
                'CREATE TABLE IF NOT EXISTS limits ('
                '  id INTEGER PRIMARY KEY AUTOINCREMENT,'
                '  app_id INTEGER NOT NULL UNIQUE REFERENCES apps(id) ON DELETE CASCADE,'
                '  limit_minutes INTEGER NOT NULL DEFAULT 60,'
                '  enabled INTEGER NOT NULL DEFAULT 1)',
                'CREATE TABLE IF NOT EXISTS daily_activity ('
                '  id INTEGER PRIMARY KEY AUTOINCREMENT,'
                '  app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,'
                '  date TEXT NOT NULL,'
                '  total_seconds INTEGER NOT NULL DEFAULT 0,'
                '  UNIQUE(app_id, date))',
                'CREATE TABLE IF NOT EXISTS settings ('
                '  key TEXT PRIMARY KEY,'
                '  value TEXT)',
                'CREATE TABLE IF NOT EXISTS admins ('
                '  id INTEGER PRIMARY KEY AUTOINCREMENT,'
                '  username TEXT NOT NULL UNIQUE,'
                '  password_hash TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS excluded_apps ('
                '  id INTEGER PRIMARY KEY AUTOINCREMENT,'
                '  system_id TEXT NOT NULL UNIQUE,'
                '  display_name TEXT)',
                'CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_activity(date)',
                'CREATE INDEX IF NOT EXISTS idx_daily_app ON daily_activity(app_id)',
                'CREATE INDEX IF NOT EXISTS idx_apps_system_id ON apps(system_id)',
            ]
            for stmt in statements:
                try:
                    conn.execute(stmt)
                except Exception as e:
                    logger.warning(f'Ошибка выполнения SQL: {e} | {stmt[:80]}')
            conn.commit()
            logger.debug('Таблицы БД инициализированы')

            self._migrate_daily_activity(conn)
            self._migrate_limits(conn)
            self._migrate_from_activity(conn)
        except Exception as e:
            logger.error(f'Ошибка инициализации БД: {e}')
        finally:
            conn.close()

    def _migrate_daily_activity(self, conn: sqlite3.Connection):
        try:
            cols = conn.execute("PRAGMA table_info(daily_activity)").fetchall()
            col_names = [r['name'] for r in cols]
            if 'app_id' in col_names:
                return
            logger.info('Миграция: пересоздание daily_activity с app_id...')
            conn.execute("ALTER TABLE daily_activity RENAME TO daily_activity_old")
            conn.execute("""
                CREATE TABLE daily_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
                    date TEXT NOT NULL,
                    total_seconds INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(app_id, date)
                )
            """)
            conn.execute("""
                INSERT OR IGNORE INTO apps (app_name, system_id)
                SELECT DISTINCT app_name, system_id
                FROM daily_activity_old
                WHERE system_id IS NOT NULL AND system_id != ''
            """)
            conn.commit()
            conn.execute("""
                INSERT OR IGNORE INTO daily_activity (app_id, date, total_seconds)
                SELECT a.id, o.date, o.total_seconds
                FROM daily_activity_old o
                INNER JOIN apps a ON LOWER(a.system_id) = LOWER(o.system_id)
            """)
            conn.commit()
            conn.execute("DROP TABLE daily_activity_old")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_activity(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_app ON daily_activity(app_id)")
            conn.commit()
            logger.info('Миграция: daily_activity пересоздана с app_id')
        except Exception as e:
            logger.warning(f'Миграция daily_activity не удалась: {e}')
            conn.rollback()

    def _migrate_limits(self, conn: sqlite3.Connection):
        try:
            cols = conn.execute("PRAGMA table_info(limits)").fetchall()
            col_names = [r['name'] for r in cols]
            if 'app_id' in col_names:
                return
            logger.info('Миграция: пересоздание limits с app_id...')
            old_limits = conn.execute(
                'SELECT app_name, system_id, limit_minutes, enabled FROM limits'
            ).fetchall()
            conn.execute("ALTER TABLE limits RENAME TO limits_old")
            conn.execute("""
                CREATE TABLE limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id INTEGER NOT NULL UNIQUE REFERENCES apps(id) ON DELETE CASCADE,
                    limit_minutes INTEGER NOT NULL DEFAULT 60,
                    enabled INTEGER NOT NULL DEFAULT 1
                )
            """)
            for old in old_limits:
                d = dict(old)
                sys_id = (d.get('system_id') or d['app_name']).lower()
                app = conn.execute(
                    'SELECT id FROM apps WHERE LOWER(system_id) = ?', (sys_id,)
                ).fetchone()
                if not app:
                    cursor = conn.execute(
                        'INSERT INTO apps (app_name, system_id) VALUES (?, ?)',
                        (d['app_name'], sys_id)
                    )
                    app_id = cursor.lastrowid
                else:
                    app_id = app['id']
                conn.execute(
                    'INSERT OR IGNORE INTO limits (app_id, limit_minutes, enabled) VALUES (?, ?, ?)',
                    (app_id, d['limit_minutes'], d['enabled'])
                )
            conn.commit()
            conn.execute("DROP TABLE limits_old")
            conn.commit()
            logger.info('Миграция: limits пересоздана с app_id')
        except Exception as e:
            logger.warning(f'Миграция limits не удалась: {e}')
            conn.rollback()

    def _migrate_from_activity(self, conn: sqlite3.Connection):
        try:
            has_activity = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='activity'"
            ).fetchone() is not None
            if not has_activity:
                return
        except sqlite3.OperationalError:
            return
        try:
            conn.execute("""
                INSERT OR IGNORE INTO apps (app_name, system_id, is_tracked)
                SELECT DISTINCT app_name, system_id, is_tracked
                FROM activity
                WHERE system_id IS NOT NULL AND system_id != ''
            """)
            conn.commit()
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO daily_activity (app_id, date, total_seconds)
                    SELECT a.id, act.date, act.duration_seconds
                    FROM activity act
                    INNER JOIN apps a ON LOWER(a.system_id) = LOWER(act.system_id)
                    WHERE act.duration_seconds > 0
                """)
                conn.commit()
            except sqlite3.OperationalError:
                pass
            logger.info('Миграция: данные перенесены из activity в apps/daily_activity')
        except Exception as e:
            logger.warning(f'Миграция не удалась: {e}')

    # --- Справочник приложений (apps) ---

    def _get_or_create_app(self, conn: sqlite3.Connection, app_name: str, system_id: str) -> int:
        system_id = system_id.lower()
        row = conn.execute(
            'SELECT id FROM apps WHERE LOWER(system_id) = ?', (system_id,)
        ).fetchone()
        if row:
            conn.execute('UPDATE apps SET app_name = ? WHERE id = ?', (app_name, row['id']))
            return row['id']
        cursor = conn.execute(
            'INSERT INTO apps (app_name, system_id) VALUES (?, ?)', (app_name, system_id)
        )
        return cursor.lastrowid

    def get_app_by_system_id(self, system_id: str) -> dict | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT * FROM apps WHERE LOWER(system_id) = ?', (system_id.lower(),)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_apps(self) -> list:
        conn = self._get_connection()
        try:
            rows = conn.execute('SELECT * FROM apps ORDER BY app_name').fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_tracked_apps(self) -> list:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT * FROM apps WHERE is_tracked = 1 ORDER BY app_name'
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def mark_as_tracked(self, system_id: str):
        conn = self._get_connection()
        try:
            conn.execute(
                'UPDATE apps SET is_tracked = 1 WHERE LOWER(system_id) = ?',
                (system_id.lower(),)
            )
            conn.commit()
            logger.debug(f'Приложение помечено как отслеживаемое: {system_id}')
        finally:
            conn.close()

    def mark_as_untracked(self, system_id: str):
        conn = self._get_connection()
        try:
            conn.execute(
                'UPDATE apps SET is_tracked = 0 WHERE LOWER(system_id) = ?',
                (system_id.lower(),)
            )
            conn.commit()
            logger.debug(f'Приложение помечено как неотслеживаемое: {system_id}')
        finally:
            conn.close()

    # --- Активность (daily_activity) ---

    def tick_activity(self, app_name: str, window_title: str, system_id: str):
        today = datetime.date.today().isoformat()
        system_id = system_id.lower()
        conn = self._get_connection()
        try:
            app_id = self._get_or_create_app(conn, app_name, system_id)
            conn.execute(
                'INSERT INTO daily_activity (app_id, date, total_seconds) VALUES (?, ?, 1) '
                'ON CONFLICT(app_id, date) DO UPDATE SET total_seconds = total_seconds + 1',
                (app_id, today)
            )
            conn.commit()
        finally:
            conn.close()

    def update_activity_by_system_id(self, system_id: str, duration_seconds: int):
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            app = self.get_app_by_system_id(system_id)
            if not app:
                logger.warning(f'Приложение не найдено в справочнике: {system_id}')
                return
            conn.execute(
                'INSERT INTO daily_activity (app_id, date, total_seconds) VALUES (?, ?, ?) '
                'ON CONFLICT(app_id, date) DO UPDATE SET total_seconds = total_seconds + ?',
                (app['id'], today, duration_seconds, duration_seconds)
            )
            conn.commit()
            logger.debug(f'Активность обновлена: {system_id} +{duration_seconds}с')
        finally:
            conn.close()

    def get_or_create_today_activity_by_system_id(self, system_id: str) -> dict:
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            app = self.get_app_by_system_id(system_id)
            if not app:
                return {'system_id': system_id, 'duration_seconds': 0, 'app_name': ''}
            daily = conn.execute(
                'SELECT total_seconds FROM daily_activity WHERE app_id = ? AND date = ?',
                (app['id'], today)
            ).fetchone()
            duration = daily['total_seconds'] if daily else 0
            return {
                'system_id': system_id,
                'app_name': app['app_name'],
                'duration_seconds': duration,
                'is_tracked': app['is_tracked'],
            }
        finally:
            conn.close()

    def get_today_activity(self) -> list:
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT a.app_name, a.system_id, d.total_seconds as duration_seconds '
                'FROM daily_activity d '
                'INNER JOIN apps a ON a.id = d.app_id '
                'WHERE d.date = ? AND d.total_seconds > 0 '
                'ORDER BY d.total_seconds DESC',
                (today,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_activity_for_period(self, start_date: str, end_date: str) -> list:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT a.app_name, a.system_id, '
                'SUM(d.total_seconds) as duration_seconds '
                'FROM daily_activity d '
                'INNER JOIN apps a ON a.id = d.app_id '
                'WHERE d.date >= ? AND d.date <= ? '
                'GROUP BY a.id ORDER BY duration_seconds DESC',
                (start_date, end_date)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_tracked_activity(self, date_iso: str) -> list:
        """Возвращает все отслеживаемые приложения с активностью за указанную дату.
        Если активности не было — duration_seconds = 0."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT a.system_id, a.app_name, '
                'COALESCE(d.total_seconds, 0) as duration_seconds '
                'FROM apps a '
                'LEFT JOIN daily_activity d ON a.id = d.app_id AND d.date = ? '
                'WHERE a.is_tracked = 1 '
                'ORDER BY a.app_name',
                (date_iso,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_tracked_activity_for_period(self, start_date: str, end_date: str) -> list:
        """Возвращает все отслеживаемые приложения с суммой активности за период.
        Если активности не было — duration_seconds = 0."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT a.app_name, a.system_id, '
                'COALESCE(SUM(d.total_seconds), 0) as duration_seconds '
                'FROM apps a '
                'LEFT JOIN daily_activity d ON a.id = d.app_id '
                'AND d.date >= ? AND d.date <= ? '
                'WHERE a.is_tracked = 1 '
                'GROUP BY a.id ORDER BY duration_seconds DESC',
                (start_date, end_date)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_daily_activity(self, date_iso: str) -> list:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT a.app_name, a.system_id, d.total_seconds '
                'FROM daily_activity d '
                'INNER JOIN apps a ON a.id = d.app_id '
                'WHERE d.date = ? AND d.total_seconds > 0 '
                'ORDER BY d.total_seconds DESC',
                (date_iso,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_daily_activity_for_period(self, start_date: str, end_date: str) -> list:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT a.app_name, a.system_id, '
                'SUM(d.total_seconds) as total_seconds '
                'FROM daily_activity d '
                'INNER JOIN apps a ON a.id = d.app_id '
                'WHERE d.date >= ? AND d.date <= ? '
                'GROUP BY a.id ORDER BY total_seconds DESC',
                (start_date, end_date)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_tracked_daily_activity_for_period(self, start_date: str, end_date: str) -> list:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT a.app_name, a.system_id, '
                'SUM(d.total_seconds) as total_seconds '
                'FROM daily_activity d '
                'INNER JOIN apps a ON a.id = d.app_id '
                'WHERE d.date >= ? AND d.date <= ? AND a.is_tracked = 1 '
                'GROUP BY a.id ORDER BY total_seconds DESC',
                (start_date, end_date)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_daily_activity_for_app_by_system_id(self, system_id: str, start_date: str, end_date: str) -> list:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT d.date, d.total_seconds '
                'FROM daily_activity d '
                'INNER JOIN apps a ON a.id = d.app_id '
                'WHERE LOWER(a.system_id) = ? AND d.date >= ? AND d.date <= ? '
                'ORDER BY d.date',
                (system_id.lower(), start_date, end_date)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Лимиты ---

    def get_limit_by_system_id(self, system_id: str) -> dict | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT l.*, a.app_name, a.system_id '
                'FROM limits l '
                'INNER JOIN apps a ON a.id = l.app_id '
                'WHERE LOWER(a.system_id) = ?',
                (system_id.lower(),)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_limits(self) -> list:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT l.*, a.app_name, a.system_id '
                'FROM limits l '
                'INNER JOIN apps a ON a.id = l.app_id '
                'ORDER BY a.app_name'
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def set_limit(self, system_id: str, limit_minutes: int, enabled: bool = True, app_name: str = ""):
        conn = self._get_connection()
        try:
            system_id = system_id.lower()
            app = self.get_app_by_system_id(system_id)
            if app:
                app_id = app['id']
                if app_name:
                    conn.execute('UPDATE apps SET app_name = ? WHERE id = ?', (app_name, app_id))
            else:
                cursor = conn.execute(
                    'INSERT INTO apps (app_name, system_id) VALUES (?, ?)',
                    (app_name or system_id, system_id)
                )
                app_id = cursor.lastrowid
            conn.execute(
                'INSERT INTO limits (app_id, limit_minutes, enabled) VALUES (?, ?, ?) '
                'ON CONFLICT(app_id) DO UPDATE SET limit_minutes = ?, enabled = ?',
                (app_id, limit_minutes, int(enabled), limit_minutes, int(enabled))
            )
            conn.execute('UPDATE apps SET is_tracked = 1 WHERE id = ?', (app_id,))
            conn.commit()
            logger.debug(f'Лимит сохранён: {system_id} = {limit_minutes} мин (enabled={enabled})')
        finally:
            conn.close()

    def delete_limit_by_system_id(self, system_id: str):
        conn = self._get_connection()
        try:
            conn.execute(
                'DELETE FROM limits WHERE app_id IN '
                '(SELECT id FROM apps WHERE LOWER(system_id) = ?)',
                (system_id.lower(),)
            )
            conn.commit()
            logger.debug(f'Лимит удалён: {system_id}')
        finally:
            conn.close()

    # --- Исключения ---

    def get_excluded_apps(self) -> list:
        conn = self._get_connection()
        try:
            rows = conn.execute('SELECT * FROM excluded_apps ORDER BY system_id').fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def add_excluded_app(self, system_id: str, display_name: str = ""):
        system_id = system_id.lower()
        conn = self._get_connection()
        try:
            conn.execute(
                'INSERT OR IGNORE INTO excluded_apps (system_id, display_name) VALUES (?, ?)',
                (system_id, display_name)
            )
            conn.execute(
                'DELETE FROM daily_activity WHERE app_id IN '
                '(SELECT id FROM apps WHERE LOWER(system_id) = ?)',
                (system_id,)
            )
            conn.execute(
                'DELETE FROM apps WHERE LOWER(system_id) = ?',
                (system_id,)
            )
            conn.commit()
            logger.debug(f'Приложение добавлено в исключения: {system_id} ({display_name})')
        finally:
            conn.close()

    def remove_excluded_app(self, system_id: str):
        conn = self._get_connection()
        try:
            conn.execute('DELETE FROM excluded_apps WHERE LOWER(system_id) = ?', (system_id.lower(),))
            conn.commit()
            logger.debug(f'Приложение удалено из исключений: {system_id}')
        finally:
            conn.close()

    def is_app_excluded(self, system_id: str) -> bool:
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT 1 FROM excluded_apps WHERE LOWER(system_id) = ?', (system_id.lower(),)
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    # --- Сброс ---

    def reset_today(self):
        today = datetime.date.today().isoformat()
        conn = self._get_connection()
        try:
            conn.execute('DELETE FROM daily_activity WHERE date = ?', (today,))
            conn.commit()
            logger.info(f'Активность за {today} сброшена')
        finally:
            conn.close()

    def remove_old_activity(self, date_iso: str, active_system_ids: set):
        conn = self._get_connection()
        try:
            if not active_system_ids:
                return
            placeholders = ','.join('?' * len(active_system_ids))
            deleted = conn.execute(
                f'DELETE FROM daily_activity WHERE date = ? AND app_id NOT IN '
                f'(SELECT id FROM apps WHERE LOWER(system_id) IN ({placeholders}))',
                (date_iso, *[s.lower() for s in active_system_ids])
            ).rowcount
            conn.commit()
            if deleted:
                logger.debug(f'Удалено {deleted} устаревших записей активности за {date_iso}')
        finally:
            conn.close()

    # --- Настройки ---

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

    # --- Администраторы ---

    def _ensure_default_admin(self):
        """Создать администратора по умолчанию, если нет ни одного."""
        conn = self._get_connection()
        try:
            row = conn.execute('SELECT 1 FROM admins LIMIT 1').fetchone()
            if row is None:
                from core.auth import hash_password
                conn.execute(
                    'INSERT OR IGNORE INTO admins (username, password_hash) VALUES (?, ?)',
                    ('admin', hash_password('admin'))
                )
                conn.commit()
                logger.info('Создан администратор по умолчанию: admin / admin')
        finally:
            conn.close()

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

    def get_admin(self, username: str) -> dict | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT * FROM admins WHERE username = ?', (username,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def admin_exists(self) -> bool:
        conn = self._get_connection()
        try:
            row = conn.execute('SELECT 1 FROM admins LIMIT 1').fetchone()
            return row is not None
        finally:
            conn.close()

    def close(self):
        logger.debug('Database.close() вызван')
        pass
