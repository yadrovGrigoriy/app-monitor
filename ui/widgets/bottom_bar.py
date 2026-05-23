from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt5.QtCore import pyqtSignal



class BottomBar(QWidget):
    """Нижняя панель с кнопками."""
    settings_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    stats_clicked = pyqtSignal()
    auth_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)


        self.btn_settings = QPushButton('Настройки')
        self.btn_settings.clicked.connect(self.settings_clicked)
        layout.addWidget(self.btn_settings)

        self.btn_stats = QPushButton('Статистика')
        self.btn_stats.clicked.connect(self.stats_clicked)
        layout.addWidget(self.btn_stats)

        self.btn_refresh = QPushButton('Обновить')
        self.btn_refresh.clicked.connect(self.refresh_clicked)
        layout.addWidget(self.btn_refresh)

        layout.addStretch()

        self.btn_auth = QPushButton('🔒 Авторизация')
        self.btn_auth.clicked.connect(self.auth_clicked)
        layout.addWidget(self.btn_auth)

    def set_auth_state(self, is_admin: bool):
        """Обновить состояние кнопки авторизации."""
        if is_admin:
            self.btn_auth.setText('🔓 Выход')
            self.btn_auth.setStyleSheet('color: #d13438; font-weight: bold;')
        else:
            self.btn_auth.setText('🔒 Авторизация')
            self.btn_auth.setStyleSheet('')
