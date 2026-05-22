"""Глобальные стили для UI."""

COLOR_DANGER = "#d13438"
COLOR_SUCCESS = "#107c10"
COLOR_TEXT_SECONDARY = "#616161"
COLOR_ACCENT = "#0078d4"
COLOR_BORDER = "#c0c0c0"
COLOR_BORDER_LIGHT = "#e0e0e0"
COLOR_BG_BUTTON = "#f0f0f0"
COLOR_BG_TAB = "#f5f5f5"

# Стиль для окон (SettingsDialog, диалоги авторизации)
GLOBAL_STYLE = f"""
    QDialog, QTabWidget, QWidget {{
        font-size: 13px;
    }}
    QPushButton {{
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 6px 20px;
        background: {COLOR_BG_BUTTON};
    }}
    QPushButton:hover {{
        background: #e5e5e5;
    }}
    QPushButton:pressed {{
        background: #d5d5d5;
    }}
    QLineEdit, QSpinBox, QComboBox, QDateEdit, QTimeEdit, QDoubleSpinBox {{
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        min-height: 24px;
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus {{
        border-color: {COLOR_ACCENT};
    }}
    QGroupBox {{
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-radius: 8px;
        margin-top: 12px;
        padding: 16px 12px 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}
    QTableWidget {{
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-radius: 8px;
        gridline-color: #f0f0f0;
    }}
    QTableWidget::item {{
        padding: 6px 10px;
    }}
    QTableView {{
        border-radius: 8px;
    }}
    QHeaderView::section {{
        border: none;
        border-bottom: 1px solid {COLOR_BORDER_LIGHT};
        padding: 8px 10px;
        font-weight: 600;
    }}
    QTabWidget::pane {{
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-radius: 8px;
        padding: 12px;
    }}
    QTabBar::tab {{
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 20px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: #ffffff;
        border-bottom: 2px solid {COLOR_ACCENT};
    }}
    QTabBar::tab:!selected {{
        background: {COLOR_BG_TAB};
    }}
    QCheckBox {{
        spacing: 8px;
    }}
"""

# Стиль для главного окна (инпуты)
MAIN_WINDOW_INPUT_STYLE = f"""
    QLineEdit, QSpinBox, QComboBox, QDateEdit, QTimeEdit, QDoubleSpinBox {{
        border-radius: 6px;
        border: 1px solid {COLOR_BORDER_LIGHT};
        padding: 4px 8px;
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus {{
        border-color: {COLOR_ACCENT};
    }}
"""
