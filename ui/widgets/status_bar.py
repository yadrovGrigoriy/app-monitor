"""Панель состояния с индикаторами статуса."""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen

from core.logger import setup_logger

logger = setup_logger('ui.widgets.status_bar')

COLOR_GREEN = "#27ae60"
COLOR_RED = "#e74c3c"
COLOR_YELLOW = "#f39c12"
COLOR_GRAY = "#95a5a6"


class _StatusIndicator(QWidget):
    """Круглый индикатор состояния."""

    def __init__(self, color: str = COLOR_GRAY, size: int = 10, parent=None):
        super().__init__(parent)
        self._color = color
        self._size = size
        self.setFixedSize(size + 4, size + 4)

    def set_color(self, color: str):
        self._color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(self._color)))
        painter.setPen(QPen(QColor(self._color), 1))
        r = self._size // 2
        cx, cy = self.width() // 2, self.height() // 2
        painter.drawEllipse(cx - r, cy - r, self._size, self._size)


class StatusBar(QWidget):
    """Панель состояния с индикаторами сервера, мониторинга и ошибок."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server_host = "0.0.0.0"
        self._server_port = 8765
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # ── Веб-сервер ──────────────────────────────────────────────
        self._server_indicator = _StatusIndicator(COLOR_GRAY)
        layout.addWidget(self._server_indicator)

        self._server_label = QLabel("Сервер: запуск…")
        self._server_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        layout.addWidget(self._server_label)

        # Разделитель
        sep1 = QLabel("|")
        sep1.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        layout.addWidget(sep1)

        # ── Мониторинг ──────────────────────────────────────────────
        self._monitor_indicator = _StatusIndicator(COLOR_GRAY)
        layout.addWidget(self._monitor_indicator)

        self._monitor_label = QLabel("Мониторинг: запуск…")
        self._monitor_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        layout.addWidget(self._monitor_label)

        # Разделитель
        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        layout.addWidget(sep2)

        # ── Ошибки ──────────────────────────────────────────────────
        self._error_indicator = _StatusIndicator(COLOR_GREEN)
        layout.addWidget(self._error_indicator)

        self._error_label = QLabel("Ошибок нет")
        self._error_label.setStyleSheet("color: #27ae60; font-size: 11px;")
        layout.addWidget(self._error_label)

        layout.addStretch()

        # IP-адрес
        self._ip_label = QLabel("")
        self._ip_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(self._ip_label)

    # ── Публичные методы ────────────────────────────────────────────

    def set_server_status(self, running: bool, host: str = "0.0.0.0", port: int = 8765):
        """Обновить статус веб-сервера."""
        self._server_host = host
        self._server_port = port
        if running:
            self._server_indicator.set_color(COLOR_GREEN)
            self._server_label.setText(f"Сервер: {host}:{port}")
            self._server_label.setStyleSheet("color: #27ae60; font-size: 11px;")
        else:
            self._server_indicator.set_color(COLOR_RED)
            self._server_label.setText("Сервер: остановлен")
            self._server_label.setStyleSheet("color: #e74c3c; font-size: 11px;")

    def set_monitor_status(self, running: bool, apps_count: int = 0):
        """Обновить статус мониторинга."""
        if running:
            self._monitor_indicator.set_color(COLOR_GREEN)
            text = f"Мониторинг: активен"
            if apps_count:
                text += f" ({apps_count} прил.)"
            self._monitor_label.setText(text)
            self._monitor_label.setStyleSheet("color: #27ae60; font-size: 11px;")
        else:
            self._monitor_indicator.set_color(COLOR_RED)
            self._monitor_label.setText("Мониторинг: остановлен")
            self._monitor_label.setStyleSheet("color: #e74c3c; font-size: 11px;")

    def set_error_status(self, has_errors: bool, count: int = 0, last_error: str = ""):
        """Обновить статус ошибок."""
        if has_errors:
            self._error_indicator.set_color(COLOR_RED)
            text = f"Ошибки: {count}"
            if last_error:
                text += f" ({last_error})"
            self._error_label.setText(text)
            self._error_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
        else:
            self._error_indicator.set_color(COLOR_GREEN)
            self._error_label.setText("Ошибок нет")
            self._error_label.setStyleSheet("color: #27ae60; font-size: 11px;")

    def set_local_ip(self, ip: str):
        """Показать локальный IP-адрес."""
        self._ip_label.setText(f"IP: {ip}" if ip else "")
