"""
Точка входа для запуска API-сервера AppMonitor отдельно.
Запускает FastAPI/WebSocket сервер для удалённого доступа без GUI.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import Database
from api.server import AppMonitorAPI
from core.logger import setup_logger

logger = setup_logger('run_server')

API_HOST = '0.0.0.0'
API_PORT = 8765
SSL_CERT_FILE = os.path.join(os.path.dirname(__file__), 'data', 'cert.pem')
SSL_KEY_FILE = os.path.join(os.path.dirname(__file__), 'data', 'key.pem')


def main():
    parser = argparse.ArgumentParser(description='AppMonitor API-сервер')
    parser.add_argument('--host', default=API_HOST, help='Хост для привязки (по умолч. 0.0.0.0)')
    parser.add_argument('--port', type=int, default=API_PORT, help=f'Порт (по умолч. {API_PORT})')
    parser.add_argument('--ssl', action='store_true', help='Использовать HTTPS (нужны сертификаты в data/)')
    args = parser.parse_args()

    logger.info('=== AppMonitor API-сервер запуск ===')
    logger.info(f'Python: {sys.version}')
    logger.info(f'Platform: {sys.platform}')

    db = Database()
    logger.info('База данных инициализирована')

    ssl_cert = SSL_CERT_FILE if args.ssl and os.path.isfile(SSL_CERT_FILE) else None
    ssl_key = SSL_KEY_FILE if args.ssl and os.path.isfile(SSL_KEY_FILE) else None

    if ssl_cert and ssl_key:
        logger.info('SSL-сертификаты найдены, запуск по HTTPS')
    else:
        logger.info('Запуск по HTTP')

    server = AppMonitorAPI(db, host=args.host, port=args.port,
                            ssl_certfile=ssl_cert, ssl_keyfile=ssl_key)
    server.start()

    logger.info(f'API-сервер запущен на {args.host}:{args.port}')
    logger.info('Нажмите Ctrl+C для остановки')

    try:
        server._thread.join()
    except KeyboardInterrupt:
        logger.info('Получен сигнал остановки')
    finally:
        logger.info('Остановка API-сервера...')
        server.stop()
        db.close()
        logger.info('API-сервер завершён')


if __name__ == '__main__':
    main()
