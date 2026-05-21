"""
Аутентификация и авторизация для AppMonitor.
"""

import hashlib
import secrets
import time
import logging
from typing import Optional

from core.database import Database

logger = logging.getLogger('core.auth')

# Время жизни токена (часов)
TOKEN_TTL_HOURS = 24


def hash_password(password: str) -> str:
    """SHA-256 хеш пароля (с солью)."""
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f'{salt}:{password}'.encode()).hexdigest()
    return f'{salt}:{h}'


def verify_password(password: str, password_hash: str) -> bool:
    """Проверить пароль против хеша."""
    try:
        salt, h = password_hash.split(':', 1)
        expected = hashlib.sha256(f'{salt}:{password}'.encode()).hexdigest()
        return h == expected
    except (ValueError, AttributeError):
        return False


class AuthManager:
    """Управление аутентификацией администраторов."""

    def __init__(self, db: Database):
        self.db = db
        self._tokens: dict[str, dict] = {}  # token -> {username, expires_at}
        logger.debug('AuthManager создан')

    def register(self, username: str, password: str) -> bool:
        """Зарегистрировать нового администратора."""
        if self.db.get_admin(username):
            logger.warning(f'Администратор {username} уже существует')
            return False
        self.db.add_admin(username, hash_password(password))
        logger.info(f'Зарегистрирован администратор: {username}')
        return True

    def login(self, username: str, password: str) -> Optional[str]:
        """Аутентификация. Возвращает токен или None."""
        admin = self.db.get_admin(username)
        if not admin:
            logger.warning(f'Попытка входа с неизвестным логином: {username}')
            return None
        if not verify_password(password, admin['password_hash']):
            logger.warning(f'Неверный пароль для {username}')
            return None
        token = secrets.token_hex(32)
        self._tokens[token] = {
            'username': username,
            'expires_at': time.time() + TOKEN_TTL_HOURS * 3600,
        }
        logger.info(f'Администратор {username} вошёл в систему')
        return token

    def validate_token(self, token: str) -> Optional[str]:
        """Проверить токен. Возвращает username или None."""
        data = self._tokens.get(token)
        if not data:
            return None
        if time.time() > data['expires_at']:
            self._tokens.pop(token, None)
            logger.debug(f'Токен истёк: {token[:8]}...')
            return None
        return data['username']

    def logout(self, token: str):
        """Инвалидировать токен."""
        self._tokens.pop(token, None)
        logger.debug(f'Токен удалён: {token[:8]}...')

    def verify_local(self, username: str, password: str) -> bool:
        """Проверить логин/пароль локально (в мониторе)."""
        admin = self.db.get_admin(username)
        if not admin:
            return False
        return verify_password(password, admin['password_hash'])
