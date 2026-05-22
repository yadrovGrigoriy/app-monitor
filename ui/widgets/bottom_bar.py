from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt5.QtCore import pyqtSignal
from ui.breadcrumbs import component_tooltip


class BottomBar(QWidget):
    """Нижняя панель с кнопками."""
    settings_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    stats_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setToolTip(component_tooltip(self))

        btn_settings = QPushButton('Настройки')
        btn_settings.setFixedHeight(32)
        btn_settings.clicked.connect(self.settings_clicked)
        layout.addWidget(btn_settings)

        btn_stats = QPushButton('Статистика')
        btn_stats.setFixedHeight(32)
        btn_stats.clicked.connect(self.stats_clicked)
        layout.addWidget(btn_stats)

        btn_refresh = QPushButton('Обновить')
        btn_refresh.setFixedHeight(32)
        btn_refresh.clicked.connect(self.refresh_clicked)
        layout.addWidget(btn_refresh)

        layout.addStretch()
