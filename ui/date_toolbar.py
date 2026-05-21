from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QDateEdit, QPushButton
from PyQt5.QtCore import QDate, pyqtSignal


class DateToolbar(QWidget):
    """Панель выбора даты."""
    date_changed = pyqtSignal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel('Дата:'))

        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.dateChanged.connect(self.date_changed)
        layout.addWidget(self.date_picker)

        btn_today = QPushButton('Сегодня')
        btn_today.clicked.connect(lambda: self.date_picker.setDate(QDate.currentDate()))
        layout.addWidget(btn_today)

        layout.addStretch()

        self.apps_count_label = QLabel('')
        layout.addWidget(self.apps_count_label)

    def selected_date(self) -> QDate:
        return self.date_picker.date()

    def set_apps_count(self, count: int):
        self.apps_count_label.setText(f'{count} приложений')
