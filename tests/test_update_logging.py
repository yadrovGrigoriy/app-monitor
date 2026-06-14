"""Тест логирования обновлений в БД."""

import os
import tempfile
from core.database import Database
from core.updater import APP_VERSION


def test_update_logging():
    """Проверить, что при смене версии создаётся запись в истории."""
    db_path = os.path.join(tempfile.gettempdir(), 'test_update_log.db')
    if os.path.exists(db_path):
        os.remove(db_path)

    db = Database(db_path)

    # Старая версия в БД
    db.set_setting('app_version', '1.0.0')

    prev = db.get_setting('app_version', '')
    assert prev == '1.0.0', f'Ожидалась 1.0.0, получено {prev}'

    # Симулируем запуск с новой версией
    if prev and prev != APP_VERSION:
        db.add_update_record(prev, APP_VERSION)
        db.set_setting('app_version', APP_VERSION)

    # Проверяем историю
    history = db.get_update_history()
    assert len(history) == 1, f'Ожидалась 1 запись, получено {len(history)}'

    record = history[0]
    assert record['old_version'] == '1.0.0', f'old_version: {record["old_version"]}'
    assert record['new_version'] == APP_VERSION, f'new_version: {record["new_version"]}'
    assert record['date'] is not None, 'date is None'

    print(f'OK: {record["old_version"]} -> {record["new_version"]} at {record["date"]}')

    # Повторный запуск — запись не должна дублироваться
    prev2 = db.get_setting('app_version', '')
    if prev2 and prev2 != APP_VERSION:
        db.add_update_record(prev2, APP_VERSION)
    history2 = db.get_update_history()
    assert len(history2) == 1, f'Повторный запуск создал дубль: {len(history2)}'

    # Проверяем get_last_update
    last = db.get_last_update()
    assert last is not None
    assert last['new_version'] == APP_VERSION

    db.close()
    os.remove(db_path)
    print('Все проверки пройдены!')


if __name__ == '__main__':
    test_update_logging()
