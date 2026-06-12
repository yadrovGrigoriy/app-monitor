"""
Диалог информации о версии AppMonitor.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.updater import APP_VERSION
from ui.styles import global_style


class UpdateDialog(QDialog):
    """Диалог с информацией о текущей версии."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle('О программе')
        self.setMinimumSize(360, 160)
        self.resize(400, 180)
        self.setStyleSheet(global_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel('AppMonitor')
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Версия
        ver = QLabel(f'Версия {APP_VERSION}')
        ver_font = QFont()
        ver_font.setPointSize(12)
        ver.setFont(ver_font)
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        layout.addStretch()

        # Кнопка закрытия
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton('Закрыть')
        btn_close.clicked.connect(self.accept)
        btn_close.setFixedWidth(120)
        btn_layout.addWidget(btn_close)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
