from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QAction
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QCursor

from ui.styles import table_style

COLOR_SUCCESS = "#107c10"
COLOR_DANGER = "#d13438"
COLOR_TEXT_SECONDARY = "#616161"


class TrackedTable(QTableWidget):
    """Таблица отслеживаемых приложений."""
    remove_requested = pyqtSignal(str)  # system_id
    add_limit_requested = pyqtSignal(str)  # app_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):

        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(['Имя процесса', 'Приложение', 'Время', 'Лимит', 'Осталось'])
        self.cellDoubleClicked.connect(self._on_double_click)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.setStyleSheet(table_style())
        self.verticalHeader().setDefaultSectionSize(40)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def populate(self, items: list[dict], limits: dict):
        """Заполнить таблицу отслеживаемых приложений.
        Каждый элемент: {'system_id': ..., 'app_name': ..., 'duration_seconds': ...}
        limits: dict[app_name] -> {'limit_minutes': ..., 'enabled': ...}
        """
        self.setRowCount(len(items))
        for i, item in enumerate(items):
            self._set_system_id_row(i, item)
            self._set_app_name_row(i, item)
            self._set_duration_row(i, item)
            self._set_limit_row(i, item, limits)
            self._set_remaining_row(i, item, limits)
        self.resizeRowsToContents()

    def _set_system_id_row(self, row: int, item: dict):
        sys_id = item.get('system_id', '')
        sys_item = QTableWidgetItem(sys_id if sys_id else '—')
        sys_item.setTextAlignment(Qt.AlignCenter)
        sys_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
        self.setItem(row, 0, sys_item)

    def _set_app_name_row(self, row: int, item: dict):
        name_item = QTableWidgetItem(item['app_name'])
        name_item.setForeground(QColor('#000000'))
        self.setItem(row, 1, name_item)

    def _set_duration_row(self, row: int, item: dict):
        hours = item['duration_seconds'] // 3600
        minutes = (item['duration_seconds'] % 3600) // 60
        seconds = item['duration_seconds'] % 60
        time_str = f'{hours}:{minutes:02d}:{seconds:02d}'
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

    def _set_remaining_row(self, row: int, item: dict, limits: dict):
        limit = limits.get(item['app_name'])
        remaining_item = QTableWidgetItem()
        remaining_item.setTextAlignment(Qt.AlignCenter)
        if limit and limit['enabled']:
            used = item['duration_seconds'] // 60
            left = max(0, limit['limit_minutes'] - used)
            remaining_item.setText(f'{left} мин')
            if left == 0:
                remaining_item.setForeground(QColor(COLOR_DANGER))
            else:
                remaining_item.setForeground(QColor(COLOR_SUCCESS))
        else:
            remaining_item.setText('—')
            remaining_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
        self.setItem(row, 4, remaining_item)

    def _on_double_click(self, row: int, column: int):
        """При двойном клике — предложить добавить лимит."""
        name_item = self.item(row, 1)
        if name_item and name_item.text():
            self.add_limit_requested.emit(name_item.text())

    def _on_context_menu(self, pos):
        row = self.rowAt(pos.y())
        if row < 0:
            return

        sys_id_item = self.item(row, 0)
        name_item = self.item(row, 1)
        if not sys_id_item or not name_item:
            return

        system_id = sys_id_item.text()
        app_name = name_item.text()

        menu = QMenu(self)

        action_add_limit = QAction('Добавить лимит', self)
        action_add_limit.triggered.connect(lambda: self.add_limit_requested.emit(app_name))
        menu.addAction(action_add_limit)

        action_remove = QAction('Удалить', self)
        action_remove.triggered.connect(lambda: self.remove_requested.emit(system_id))
        menu.addAction(action_remove)

        menu.exec_(QCursor.pos())
