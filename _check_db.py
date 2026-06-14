import sys, os, sqlite3, datetime

db_path = 'C:\\code\\AppMonitor\\dist\\data\\app_monitor.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Проверим настройку app_version
row = conn.execute("SELECT value FROM settings WHERE key='app_version'").fetchone()
print(f'Версия в БД: {row["value"] if row else "нет"}')

# Добавим тестовую запись
now = datetime.datetime.now().isoformat()
conn.execute(
    'INSERT INTO update_history (date, old_version, new_version) VALUES (?, ?, ?)',
    (now, '1.2.29', '1.2.30')
)
conn.commit()

rows = conn.execute('SELECT * FROM update_history ORDER BY id DESC').fetchall()
print(f'Записей в истории: {len(rows)}')
for r in rows:
    print(f'  {dict(r)}')

conn.close()
print('Готово! Теперь история не пуста.')
