from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QDateEdit, QPushButton, QComboBox
from PyQt5.QtCore import QDate, pyqtSignal, Qt
from ui.breadcrumbs import component_tooltip


class DateToolbar(QWidget):
    """Панель выбора даты и периода."""
    date_changed = pyqtSignal(QDate)
    period_changed = pyqtSignal(str)  # 'day', 'week', 'month', 'year'

    PERIODS = [
        ('day', 'День'),
        ('week', 'Неделя'),
        ('month', 'Месяц'),
        ('year', 'Год'),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_period = 'day'
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setToolTip(component_tooltip(self))

        layout.addWidget(QLabel('Период:'))

        self.period_combo = QComboBox()
        for value, label in self.PERIODS:
            self.period_combo.addItem(label, value)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        layout.addWidget(self.period_combo)

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
        self.apps_count_label.setStyleSheet('color: #666; font-size: 13px;')
        layout.addWidget(self.apps_count_label)

    def _on_period_changed(self, index: int):
        self._current_period = self.period_combo.itemData(index)
        self.period_changed.emit(self._current_period)

    def selected_date(self) -> QDate:
        return self.date_picker.date()

    def current_period(self) -> str:
        return self._current_period

    def set_apps_count(self, count: int):
        self.apps_count_label.setText(f'{count} приложений')
