"""Глобальные стили для UI.

Базовую тему (кнопки, поля ввода, цвета) предоставляет PyQtDarkTheme (qdarktheme).
Здесь — только специфические переопределения для кастомных компонентов проекта.
Цвета адаптируются под текущую тему (светлая/тёмная).
"""

from ui.theme_manager import THEME_DARK


# ── Цвета (используются в коде для подсветки строк, иконок и т.д.) ────
COLOR_DANGER = "#d13438"
COLOR_SUCCESS = "#107c10"
COLOR_TEXT_SECONDARY = "#616161"
COLOR_ACCENT = "#0078d4"


def _theme_colors(is_dark: bool) -> dict:
    """Вернуть словарь цветов в зависимости от темы."""
    if is_dark:
        return {
            "bg_primary": "#1e1e1e",
            "bg_secondary": "#2d2d2d",
            "bg_tab": "#2d2d2d",
            "bg_widget": "#252526",
            "bg_hover": "#383838",
            "text_primary": "#e0e0e0",
            "text_secondary": "#9e9e9e",
            "border": "#3c3c3c",
            "border_light": "#3c3c3c",
            "bg_button": "#333333",
            "bg_table_alt": "#2d2d2d",
            "white": "#1e1e1e",
            "tab_selected_bg": "#2d2d2d",
            "tab_selected_border": COLOR_ACCENT,
        }
    else:
        return {
            "bg_primary": "#ffffff",
            "bg_secondary": "#f5f5f5",
            "bg_tab": "#f5f5f5",
            "bg_widget": "#ffffff",
            "bg_hover": "#e8e8e8",
            "text_primary": "#000000",
            "text_secondary": "#616161",
            "border": "#c0c0c0",
            "border_light": "#e0e0e0",
            "bg_button": "#f5f5f5",
            "bg_table_alt": "#f5f5f5",
            "white": "#ffffff",
            "tab_selected_bg": "#ffffff",
            "tab_selected_border": COLOR_ACCENT,
        }


def _is_dark_theme() -> bool:
    """Определить, активна ли тёмная тема."""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return True  # по умолчанию тёмная
    # Проверяем через палитру — у тёмной темы тёмный фон окна
    bg = app.palette().window().color()
    return bg.lightness() < 128


def global_style(is_dark: bool | None = None) -> str:
    """Сгенерировать глобальный стиль с учётом темы."""
    if is_dark is None:
        is_dark = _is_dark_theme()
    c = _theme_colors(is_dark)

    return f"""
    QDialog, QTabWidget, QWidget {{
        font-size: 13px;
    }}
    QGroupBox {{
        border: 1px solid {c["border_light"]};
        border-radius: 8px;
        margin-top: 10px;
        padding: 15px 10px 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}
    QTableWidget {{
        border: 1px solid {c["border_light"]};
        border-radius: 8px;
        gridline-color: {c["border_light"]};
    }}
    QTableWidget::item {{
        padding: 6px 10px;
    }}
    QTableView {{
        border-radius: 8px;
    }}
    QHeaderView::section {{
        border: none;
        border-bottom: 1px solid {c["border_light"]};
        padding: 8px 10px;
        font-weight: 600;
    }}
    QTabWidget::pane {{
        border: 1px solid {c["border_light"]};
        border-radius: 8px;
        padding: 12px;
    }}
    QTabBar::tab {{
        border: 1px solid {c["border_light"]};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 20px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {c["tab_selected_bg"]};
        border-bottom: 2px solid {c["tab_selected_border"]};
    }}
    QTabBar::tab:!selected {{
        background: {c["bg_tab"]};
    }}
    QCheckBox {{
        spacing: 8px;
    }}
    QTableWidget {{
        alternate-background-color: {c["bg_table_alt"]};
    }}
    QTableWidget::item:selected {{
        background-color: {COLOR_ACCENT}40;
    }}
    """


def table_style(is_dark: bool | None = None) -> str:
    """Стиль для таблиц ActivityTable и TrackedTable."""
    if is_dark is None:
        is_dark = _is_dark_theme()
    c = _theme_colors(is_dark)

    return f"""
    QTableWidget {{
        font-size: 13px;
        border-radius: 8px;
        border: 1px solid {c["border_light"]};
        alternate-background-color: {c["bg_table_alt"]};
    }}
    QTableWidget::item {{
        padding: 8px 20px;
        min-height: 28px;
    }}
    QTableWidget::item:selected {{
        background-color: {COLOR_ACCENT}40;
    }}
    QHeaderView::section {{
        font-weight: 600;
        padding: 8px 20px;
        border: none;
        border-bottom: 1px solid {c["border_light"]};
    }}
    """


def tab_table_style(is_dark: bool | None = None) -> str:
    """Стиль для таблиц на вкладках главного окна."""
    if is_dark is None:
        is_dark = _is_dark_theme()
    c = _theme_colors(is_dark)

    return f"""
    QTableWidget {{
        border: 1px solid {c["border_light"]};
        border-radius: 6px;
        font-size: 13px;
        alternate-background-color: {c["bg_table_alt"]};
    }}
    QTableWidget::item {{
        padding: 6px 12px;
    }}
    QTableWidget::item:selected {{
        background-color: {COLOR_ACCENT}40;
    }}
    QHeaderView::section {{
        font-weight: 600;
        padding: 6px 12px;
        border: none;
        border-bottom: 1px solid {c["border_light"]};
    }}
    """


# Для обратной совместимости — старые константы
GLOBAL_STYLE = global_style()
