"""
Менеджер ролей для AppMonitor.
Роли: admin (полный доступ), user (только просмотр).
"""

from core.database import Database
from core.logger import setup_logger

logger = setup_logger('core.role_manager')

ROLE_SETTING_KEY = 'app_role'
ROLE_ADMIN = 'admin'
ROLE_USER = 'user'


class RoleManager:
    """Управление ролями пользователей."""

    def __init__(self, db: Database):
        self.db = db
        logger.debug('RoleManager создан')

    def get_role(self) -> str:
        """Вернуть текущую роль (admin/user)."""
        if self.db is None:
            return ROLE_ADMIN
        role = self.db.get_setting(ROLE_SETTING_KEY, ROLE_ADMIN)
        if role not in (ROLE_ADMIN, ROLE_USER):
            role = ROLE_ADMIN
        return role

    def set_role(self, role: str):
        """Установить роль."""
        if role not in (ROLE_ADMIN, ROLE_USER):
            logger.warning(f'Попытка установить неизвестную роль: {role}')
            return
        if self.db is None:
            logger.debug('RoleManager: db is None, роль не сохраняется (AdminUI)')
            return
        self.db.set_setting(ROLE_SETTING_KEY, role)
        logger.info(f'Роль изменена на: {role}')

    def is_admin(self) -> bool:
        return self.get_role() == ROLE_ADMIN

    def is_user(self) -> bool:
        return self.get_role() == ROLE_USER

    def toggle(self) -> str:
        """Переключить роль. Вернуть новую роль."""
        current = self.get_role()
        new_role = ROLE_USER if current == ROLE_ADMIN else ROLE_ADMIN
        self.set_role(new_role)
        return new_role
