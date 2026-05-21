from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QApplication
from PyQt5.QtCore import pyqtSignal


class BottomBar(QWidget):
    """Нижняя панель с кнопками."""
    settings_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_settings = QPushButton('Настройки')
        btn_settings.clicked.connect(self.settings_clicked)
        layout.addWidget(btn_settings)

        btn_refresh = QPushButton('Обновить')
        btn_refresh.clicked.connect(self.refresh_clicked)
        layout.addWidget(btn_refresh)

        layout.addStretch()

        btn_quit = QPushButton('Выйти')
        btn_quit.clicked.connect(QApplication.instance().quit)
        layout.addWidget(btn_quit)
