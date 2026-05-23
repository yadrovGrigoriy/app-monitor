import logging
import sys
import os
from datetime import datetime

# Приоритет: папка рядом с exe (для разработки), иначе %APPDATA%
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.access(_base, os.W_OK):
    _base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AppMonitor')

LOG_DIR = os.path.join(_base, 'logs')
LOG_FILE = os.path.join(LOG_DIR, f'appmonitor_{datetime.now().strftime("%Y%m%d")}.log')


def setup_logger(name: str) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Проверяем, есть ли уже корневые хендлеры
    root = logging.getLogger()
    if not root.handlers:
        # Файловый handler — всё подряд
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        file_handler.setFormatter(file_fmt)
        root.addHandler(file_handler)

        # Консольный handler — DEBUG и выше
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_fmt = logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_fmt)
        root.addHandler(console_handler)

    # Чтобы сообщения от дочерних логгеров не дублировались,
    # отключаем propagation, если у логгера есть свои хендлеры
    # (сейчас хендлеров нет, всё идёт через root)
    logger.propagate = True

    return logger
