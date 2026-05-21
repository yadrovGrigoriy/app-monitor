from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

COLOR_SUCCESS = "#107c10"
COLOR_DANGER = "#d13438"
COLOR_TEXT_SECONDARY = "#616161"

STYLE_TABLE = """
    QTableWidget {
        font-size: 13px;
    }
    QTableWidget::item {
        padding: 4px 8px;
    }
    QHeaderView::section {
        font-weight: 600;
        padding: 6px 8px;
        border: none;
        border-bottom: 1px solid #e0e0e0;
    }
"""


class ActivityTable(QTableWidget):
    """Таблица активности приложений."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(['Приложение', 'Окно', 'Время', 'Лимит'])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.setStyleSheet(STYLE_TABLE)

    def populate(self, activity: list, limits: dict):
        """Заполнить таблицу данными активности."""
        self.setRowCount(len(activity))
        for i, item in enumerate(activity):
            self._set_app_name_row(i, item)
            self._set_window_title_row(i, item)
            self._set_duration_row(i, item)
            self._set_limit_row(i, item, limits)
        self.resizeRowsToContents()

    def _set_app_name_row(self, row: int, item: dict):
        name_item = QTableWidgetItem(item['app_name'])
        name_item.setForeground(QColor('#000000'))
        self.setItem(row, 0, name_item)

    def _set_window_title_row(self, row: int, item: dict):
        title_str = item.get('window_title', '') or '—'
        title_item = QTableWidgetItem(title_str)
        title_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
        title_item.setToolTip(title_str if title_str != '—' else 'Нет активного окна')
        display_str = title_str if len(title_str) < 60 else title_str[:57] + '...'
        title_item.setText(display_str)
        self.setItem(row, 1, title_item)

    def _set_duration_row(self, row: int, item: dict):
        hours = item['duration_seconds'] // 3600
        minutes = (item['duration_seconds'] % 3600) // 60
        time_str = f'{hours} ч {minutes:02d} мин'
        time_item = QTableWidgetItem(time_str)
        time_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 2, time_item)

    def _set_limit_row(self, row: int, item: dict, limits: dict):
        limit = limits.get(item['app_name'])
        limit_item = QTableWidgetItem()
        limit_item.setTextAlignment(Qt.AlignCenter)
        if limit and limit['enabled']:
            exceeded = item['duration_seconds'] // 60 >= limit['limit_minutes']
            limit_str = f'{limit["limit_minutes"]} мин'
            if exceeded:
                limit_str += ' ⚠'
                limit_item.setForeground(QColor(COLOR_DANGER))
                limit_item.setBackground(QColor(COLOR_DANGER + '20'))
            else:
                limit_item.setForeground(QColor(COLOR_SUCCESS))
        else:
            limit_str = '—'
            limit_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
        limit_item.setText(limit_str)
        self.setItem(row, 3, limit_item)
