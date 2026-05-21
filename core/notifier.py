from PyQt5.QtWidgets import QSystemTrayIcon, QMessageBox
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
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Warning, 10000)
            logger.debug('Уведомление отправлено через трей')
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.exec_()
            logger.debug('Уведомление отправлено через QMessageBox')

    def show_info(self, title: str, message: str):
        logger.info(f'Уведомление: {title} - {message}')
        if self.tray_icon and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 5000)
