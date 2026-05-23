"""Программно создаваемая иконка приложения AppMonitor."""

from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont, QIcon
from PyQt5.QtCore import Qt, QRect


def _draw_monitor_icon(size: int = 64) -> QPixmap:
    """Нарисовать иконку монитора с графиком."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    margin = size // 8
    body_rect = QRect(margin, margin, size - 2 * margin, size - 2 * margin - size // 6)

    # Корпус монитора
    painter.setPen(QPen(QColor("#0078D4"), max(1, size // 32)))
    painter.setBrush(QColor("#1a1a2e"))
    painter.drawRoundedRect(body_rect, size // 12, size // 12)

    # Экран (внутренняя область)
    screen_margin = size // 12
    screen_rect = QRect(
        body_rect.x() + screen_margin,
        body_rect.y() + screen_margin,
        body_rect.width() - 2 * screen_margin,
        body_rect.height() - 2 * screen_margin,
    )
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#16213e"))
    painter.drawRoundedRect(screen_rect, size // 20, size // 20)

    # График (линия)
    painter.setPen(QPen(QColor("#00d2ff"), max(1, size // 32)))
    painter.setBrush(Qt.NoBrush)

    chart_w = screen_rect.width()
    chart_h = screen_rect.height()
    chart_x = screen_rect.x()
    chart_y = screen_rect.y()

    # Точки графика
    points = [
        (chart_x + chart_w * 0.05, chart_y + chart_h * 0.85),
        (chart_x + chart_w * 0.20, chart_y + chart_h * 0.60),
        (chart_x + chart_w * 0.35, chart_y + chart_h * 0.75),
        (chart_x + chart_w * 0.50, chart_y + chart_h * 0.35),
        (chart_x + chart_w * 0.65, chart_y + chart_h * 0.50),
        (chart_x + chart_w * 0.80, chart_y + chart_h * 0.20),
        (chart_x + chart_w * 0.95, chart_y + chart_h * 0.40),
    ]

    for i in range(len(points) - 1):
        painter.drawLine(
            int(points[i][0]), int(points[i][1]),
            int(points[i + 1][0]), int(points[i + 1][1]),
        )

    # Точки на графике
    painter.setBrush(QColor("#00d2ff"))
    for px, py in points:
        painter.drawEllipse(int(px) - 1, int(py) - 1, 3, 3)

    # Подставка монитора
    stand_top = body_rect.bottom()
    stand_bottom = size - margin
    stand_center_x = size // 2
    stand_width = size // 6

    painter.setPen(QPen(QColor("#0078D4"), max(1, size // 32)))
    painter.setBrush(QColor("#1a1a2e"))
    # Ножка
    painter.drawRect(stand_center_x - stand_width // 4, stand_top, stand_width // 2, stand_bottom - stand_top)
    # Основание
    painter.drawRoundedRect(
        stand_center_x - stand_width,
        stand_bottom - size // 16,
        stand_width * 2,
        size // 16,
        size // 32, size // 32,
    )

    painter.end()
    return pixmap


def create_app_icon() -> QIcon:
    """Создать иконку приложения AppMonitor."""
    pixmap = _draw_monitor_icon(64)
    icon = QIcon(pixmap)
    # Добавляем версию меньшего размера для панели задач
    small_pixmap = _draw_monitor_icon(32)
    icon.addPixmap(small_pixmap)
    return icon
