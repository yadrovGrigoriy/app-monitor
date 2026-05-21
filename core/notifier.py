from PyQt5.QtWidgets import QSystemTrayIcon, QMessageBox


class Notifier:
    def __init__(self, tray_icon: QSystemTrayIcon = None):
        self.tray_icon = tray_icon

    def show_limit_notification(self, app_name: str, limit_minutes: int):
        title = 'Лимит достигнут'
        message = (f'Приложение "{app_name}" используется более {limit_minutes} минут.\n'
                    f'Пожалуйста, сделайте перерыв!')
        if self.tray_icon and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Warning, 10000)
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.exec_()
