import datetime
from collections import defaultdict

import matplotlib
matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QWidget, QSizePolicy, QCheckBox)
from PyQt5.QtCore import Qt, QDate

from core.database import Database
from ui.widgets.date_toolbar import DateToolbar
from core.logger import setup_logger

logger = setup_logger('ui.stats_dialog')

COLORS = [
    '#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f',
    '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac',
]


class StatsDialog(QDialog):
    """Диалог со статистикой активности в виде столбчатой диаграммы."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle('Статистика активности')
        self.setMinimumSize(800, 550)
        self.resize(1000, 650)
        self._init_ui()
        self._build_chart()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # Панель выбора даты/периода
        self.date_toolbar = DateToolbar()
        self.date_toolbar.date_changed.connect(self._build_chart)
        self.date_toolbar.period_changed.connect(self._build_chart)
        layout.addWidget(self.date_toolbar)

        # Верхняя панель с доп. опциями
        top_layout = QHBoxLayout()

        self.tracked_only_check = QCheckBox('Только отслеживаемые')
        self.tracked_only_check.stateChanged.connect(self._build_chart)
        top_layout.addWidget(self.tracked_only_check)

        top_layout.addStretch()

        btn_close = QPushButton('Закрыть')
        btn_close.clicked.connect(self.accept)
        top_layout.addWidget(btn_close)

        layout.addLayout(top_layout)

        # Холст для графика
        self.figure = Figure(figsize=(10, 5), dpi=100)
        self.figure.set_tight_layout(True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas, stretch=1)

    def _get_date_range(self) -> tuple[str, str]:
        """Вернуть (start_date, end_date) в ISO-формате в зависимости от выбранного периода."""
        today = datetime.date.today()
        period = self.date_toolbar.current_period()
        selected = self.date_toolbar.selected_date()
        selected_date = datetime.date(selected.year(), selected.month(), selected.day())

        if period == 'day':
            return selected_date.isoformat(), selected_date.isoformat()
        elif period == 'week':
            start = selected_date - datetime.timedelta(days=selected_date.weekday())
            end = start + datetime.timedelta(days=6)
            return start.isoformat(), end.isoformat()
        elif period == 'month':
            start = selected_date.replace(day=1)
            if selected_date.month == 12:
                end = selected_date.replace(year=selected_date.year + 1, month=1, day=1) - datetime.timedelta(days=1)
            else:
                end = selected_date.replace(month=selected_date.month + 1, day=1) - datetime.timedelta(days=1)
            return start.isoformat(), end.isoformat()
        else:  # year
            start = selected_date.replace(month=1, day=1)
            end = selected_date.replace(month=12, day=31)
            return start.isoformat(), end.isoformat()

    def _get_daily_data(self, start_date: str, end_date: str) -> list[dict]:
        """Получить активность с группировкой по дням."""
        conn = self.db._get_connection()
        try:
            rows = conn.execute(
                'SELECT d.date, a.app_name, d.total_seconds as duration_seconds '
                'FROM daily_activity d '
                'INNER JOIN apps a ON a.id = d.app_id '
                'WHERE d.date >= ? AND d.date <= ? '
                'ORDER BY d.date',
                (start_date, end_date)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _build_chart(self):
        """Построить столбчатую диаграмму."""
        start_date, end_date = self._get_date_range()
        logger.debug(f'Построение графика за период: {start_date} — {end_date}')

        # Получаем данные: все приложения или только отслеживаемые
        tracked_only = self.tracked_only_check.isChecked()
        if tracked_only:
            activity = self.db.get_tracked_activity_for_period(start_date, end_date)
        else:
            activity = self.db.get_activity_for_period(start_date, end_date)

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not activity:
            ax.text(0.5, 0.5, 'Нет данных за выбранный период',
                    ha='center', va='center', fontsize=14, color='gray')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.canvas.draw()
            return

        # Показываем все приложения (без ограничения топ-10)
        labels = []
        values = []
        colors = []

        for i, item in enumerate(activity):
            labels.append(item['app_name'])
            values.append(item['duration_seconds'] / 60)  # в минутах
            colors.append(COLORS[i % len(COLORS)])

        # Столбчатая диаграмма
        bars = ax.bar(range(len(values)), values, color=colors, edgecolor='white', linewidth=0.5)

        # Подписи значений на столбцах
        for bar, val in zip(bars, values):
            if val > 0:
                hours = int(val) // 60
                mins = int(val) % 60
                if hours > 0:
                    label = f'{hours}ч {mins}мин'
                else:
                    label = f'{mins}мин'
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                        label, ha='center', va='bottom', fontsize=9)

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=9)
        ax.set_ylabel('Минуты')
        suffix = ' (только отслеживаемые)' if tracked_only else ''
        ax.set_title(f'Активность приложений{suffix}\n{start_date} — {end_date}', fontsize=12, fontweight='bold', pad=15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.grid(True, alpha=0.3)

        self.canvas.draw()
