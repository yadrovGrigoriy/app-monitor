from PyQt5.QtWidgets import QSystemTrayIcon, QMessageBox
from PyQt5.QtCore import Qt
from core.logger import setup_logger

logger = setup_logger('core.notifier')


class Notifier:
    def __init__(self, tray_icon: QSystemTrayIcon = None):
        self.tray_icon = tray_icon
        logger.debug('Notifier создан')

    def show_limit_notification(self, app_name: str, limit_minutes: int):
        title = 'Лимит достигнут'
        message = (f'Приложение "{app_name}" используется более {limit_minutes} минут.\n'
                    f'Пожалуйста, сделайте перерыв!')
        logger.warning(f'Уведомление: {title} - {message}')
        if self.tray_icon and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Critical, 10000)
            logger.debug('Уведомление отправлено через трей')
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()
            logger.debug('Уведомление отправлено через QMessageBox')

    def show_info(self, title: str, message: str):
        logger.info(f'Уведомление: {title} - {message}')
        if self.tray_icon and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 5000)

    def show_exceeded_notification(self, app_name: str, app_title: str, limit_minutes: int,
                                    extended: int, max_extension: int,
                                    extension_step: int) -> bool:
        """
        Показать уведомление о превышении лимита через трей.
        Возвращает True (имитация продления, т.к. уведомление в трее не блокирует).
        """
        title = 'Лимит превышен'
        remaining = max_extension - extended
        if remaining > 0:
            message = (f'"{app_title}" превысило лимит {limit_minutes} мин.\n'
                       f'Продлено на {extended} мин. Можно продлить ещё на {remaining} мин.')
        else:
            message = (f'"{app_title}" превысило лимит {limit_minutes} мин.\n'
                       f'Лимит продления исчерпан. Приложение будет заблокировано через 5 минут.')

        logger.warning(f'Уведомление: {title} - {message}')
        if self.tray_icon and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Critical, 15000)
            logger.debug('Уведомление отправлено через трей')
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()
            logger.debug('Уведомление отправлено через QMessageBox')
        return True  # всегда возвращаем True — продление считается автоматическим

    def show_warning_notification(self, app_name: str, app_title: str, remaining_minutes: int):
        """Предупреждение о скором исчерпании лимита."""
        title = 'Лимит скоро закончится'
        message = (f'"{app_title}" — осталось {remaining_minutes} мин.')
        logger.warning(f'Предупреждение: {title} - {message}')
        if self.tray_icon and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Warning, 10000)
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()
