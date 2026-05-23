"""Программно создаваемая иконка приложения AppMonitor."""

from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont, QIcon, QLinearGradient
from PyQt5.QtCore import Qt, QRect, QPointF
from PyQt5.QtGui import QPolygonF


# Цветовая схема — современный градиент (AppUI)
_COLOR_BG_DARK = QColor("#0f0f1a")
_COLOR_BG_LIGHT = QColor("#1a1a2e")
_COLOR_ACCENT = QColor("#00d4ff")
_COLOR_ACCENT2 = QColor("#7b2ff7")
_COLOR_GRID = QColor("#2a2a4a")
_COLOR_TEXT = QColor("#ffffff")

# Цветовая схема для AdminUI — золотисто-оранжевая
_ADMIN_COLOR_BG_DARK = QColor("#1a0f0f")
_ADMIN_COLOR_BG_LIGHT = QColor("#2e1a1a")
_ADMIN_COLOR_ACCENT = QColor("#ff8c00")
_ADMIN_COLOR_ACCENT2 = QColor("#ffd700")
_ADMIN_COLOR_GRID = QColor("#4a2a2a")
_ADMIN_COLOR_TEXT = QColor("#ffffff")


def _draw_monitor_icon(size: int = 64) -> QPixmap:
    """Нарисовать иконку монитора с графиком."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    m = size // 10  # margin
    body = QRect(m, m, size - 2 * m, size - 2 * m - size // 5)

    # ── Корпус монитора (градиент) ────────────────────────────────
    grad = QLinearGradient(QPointF(0, 0), QPointF(size, size))
    grad.setColorAt(0.0, _COLOR_BG_DARK)
    grad.setColorAt(1.0, _COLOR_BG_LIGHT)
    painter.setPen(QPen(_COLOR_ACCENT, max(1, size // 40)))
    painter.setBrush(grad)
    painter.drawRoundedRect(body, size // 10, size // 10)

    # ── Экран ──────────────────────────────────────────────────────
    sm = size // 14
    screen = QRect(
        body.x() + sm,
        body.y() + sm,
        body.width() - 2 * sm,
        body.height() - 2 * sm,
    )
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#0a0a14"))
    painter.drawRoundedRect(screen, size // 24, size // 24)

    # ── Сетка на экране ───────────────────────────────────────────
    painter.setPen(QPen(_COLOR_GRID, 1))
    for i in range(1, 4):
        y = screen.y() + screen.height() * i // 4
        painter.drawLine(screen.x() + 2, y, screen.right() - 2, y)
    for i in range(1, 5):
        x = screen.x() + screen.width() * i // 5
        painter.drawLine(x, screen.y() + 2, x, screen.bottom() - 2)

    # ── График (столбцы) ──────────────────────────────────────────
    bar_count = 5
    bar_w = screen.width() // (bar_count * 3)
    bar_gap = bar_w * 2
    bar_base = screen.bottom() - 2
    bar_heights = [0.35, 0.65, 0.45, 0.80, 0.55]

    for i, h in enumerate(bar_heights):
        x = screen.x() + bar_gap * i + bar_gap // 2
        bh = int(screen.height() * h)
        bar_rect = QRect(x, bar_base - bh, bar_w, bh)

        bar_grad = QLinearGradient(
            QPointF(0, bar_base - bh),
            QPointF(0, bar_base),
        )
        bar_grad.setColorAt(0.0, _COLOR_ACCENT2)
        bar_grad.setColorAt(1.0, _COLOR_ACCENT)
        painter.setBrush(bar_grad)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_rect, 2, 2)

    # ── Подставка монитора ────────────────────────────────────────
    stand_top = body.bottom()
    stand_bottom = size - m
    cx = size // 2
    sw = size // 5

    painter.setPen(QPen(_COLOR_ACCENT, max(1, size // 40)))
    painter.setBrush(_COLOR_BG_LIGHT)
    # Ножка
    painter.drawRect(cx - sw // 6, stand_top, sw // 3, stand_bottom - stand_top)
    # Основание
    painter.drawRoundedRect(
        cx - sw,
        stand_bottom - size // 20,
        sw * 2,
        size // 20,
        size // 40, size // 40,
    )

    painter.end()
    return pixmap


def _draw_admin_icon(size: int = 64) -> QPixmap:
    """Нарисовать иконку админки — монитор с ключом/щитом."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    m = size // 10
    body = QRect(m, m, size - 2 * m, size - 2 * m - size // 5)

    # ── Корпус монитора (градиент) ────────────────────────────────
    grad = QLinearGradient(QPointF(0, 0), QPointF(size, size))
    grad.setColorAt(0.0, _ADMIN_COLOR_BG_DARK)
    grad.setColorAt(1.0, _ADMIN_COLOR_BG_LIGHT)
    painter.setPen(QPen(_ADMIN_COLOR_ACCENT, max(1, size // 40)))
    painter.setBrush(grad)
    painter.drawRoundedRect(body, size // 10, size // 10)

    # ── Экран ──────────────────────────────────────────────────────
    sm = size // 14
    screen = QRect(
        body.x() + sm,
        body.y() + sm,
        body.width() - 2 * sm,
        body.height() - 2 * sm,
    )
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#140a0a"))
    painter.drawRoundedRect(screen, size // 24, size // 24)

    # ── Сетка на экране ───────────────────────────────────────────
    painter.setPen(QPen(_ADMIN_COLOR_GRID, 1))
    for i in range(1, 4):
        y = screen.y() + screen.height() * i // 4
        painter.drawLine(screen.x() + 2, y, screen.right() - 2, y)
    for i in range(1, 5):
        x = screen.x() + screen.width() * i // 5
        painter.drawLine(x, screen.y() + 2, x, screen.bottom() - 2)

    # ── Символ ключа/щита на экране ───────────────────────────────
    cx = screen.center().x()
    cy = screen.center().y()
    r = min(screen.width(), screen.height()) // 3

    # Щит
    shield_points = [
        QPointF(cx, cy - r),
        QPointF(cx + r, cy - r // 2),
        QPointF(cx + r, cy + r // 3),
        QPointF(cx, cy + r),
        QPointF(cx - r, cy + r // 3),
        QPointF(cx - r, cy - r // 2),
    ]
    shield_grad = QLinearGradient(QPointF(cx - r, cy), QPointF(cx + r, cy))
    shield_grad.setColorAt(0.0, _ADMIN_COLOR_ACCENT2)
    shield_grad.setColorAt(1.0, _ADMIN_COLOR_ACCENT)
    painter.setBrush(shield_grad)
    painter.setPen(QPen(QColor("#ffffff"), max(1, size // 50)))
    polygon = QPolygonF(shield_points)
    painter.drawPolygon(polygon)

    # Галочка внутри щита
    pen_check = QPen(QColor("#ffffff"), max(2, size // 20))
    pen_check.setCapStyle(Qt.RoundCap)
    painter.setPen(pen_check)
    painter.setBrush(Qt.NoBrush)
    cx_f = float(cx)
    cy_f = float(cy)
    painter.drawLine(
        QPointF(cx_f - r * 0.3, cy_f),
        QPointF(cx_f - r * 0.05, cy_f + r * 0.35),
    )
    painter.drawLine(
        QPointF(cx_f - r * 0.05, cy_f + r * 0.35),
        QPointF(cx_f + r * 0.4, cy_f - r * 0.3),
    )

    # ── Подставка монитора ────────────────────────────────────────
    stand_top = body.bottom()
    stand_bottom = size - m
    cx = size // 2
    sw = size // 5

    painter.setPen(QPen(_ADMIN_COLOR_ACCENT, max(1, size // 40)))
    painter.setBrush(_ADMIN_COLOR_BG_LIGHT)
    painter.drawRect(cx - sw // 6, stand_top, sw // 3, stand_bottom - stand_top)
    painter.drawRoundedRect(
        cx - sw,
        stand_bottom - size // 20,
        sw * 2,
        size // 20,
        size // 40, size // 40,
    )

    painter.end()
    return pixmap


def create_app_icon() -> QIcon:
    """Создать иконку приложения AppMonitor (пользовательский режим)."""
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_draw_monitor_icon(s))
    return icon


def create_admin_icon() -> QIcon:
    """Создать иконку для AdminUI (режим администратора)."""
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_draw_admin_icon(s))
    return icon
