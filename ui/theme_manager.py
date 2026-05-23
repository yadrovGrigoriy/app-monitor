"""Управление темой приложения (PyQtDarkTheme)."""

import qdarktheme
from PyQt5.QtWidgets import QApplication
from core.logger import setup_logger

logger = setup_logger('ui.theme_manager')

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_SETTING_KEY = "app_theme"


def apply_theme(app: QApplication, theme: str):
    """Применить тему PyQtDarkTheme ко всему приложению."""
    # Сначала применяем qdarktheme
    app.setStyleSheet(qdarktheme.load_stylesheet(theme))
    app.setPalette(qdarktheme.load_palette(theme))

    # Переприменяем стили ко всем окнам, у которых есть refresh_styles
    for widget in app.topLevelWidgets():
        if hasattr(widget, 'refresh_styles'):
            try:
                widget.refresh_styles()
            except Exception:
                pass

    logger.info(f'Тема применена: {theme}')
