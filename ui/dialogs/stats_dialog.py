import datetime
from collections import defaultdict

import matplotlib
matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QPushButton, QLabel, QWidget, QSizePolicy)
from PyQt5.QtCore import Qt

from core.database import Database
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

        # Верхняя панель с выбором периода
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel('Период:'))

        self.period_combo = QComboBox()
        self.period_combo.addItems(['Сегодня', 'Вчера', 'Последние 7 дней', 'Последние 30 дней', 'Текущий месяц'])
        self.period_combo.currentIndexChanged.connect(self._build_chart)
        top_layout.addWidget(self.period_combo)

        top_layout.addStretch()

        btn_close = QPushButton('Закрыть')
        btn_close.setFixedHeight(32)
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
        idx = self.period_combo.currentIndex()

        if idx == 0:  # Сегодня
            return today.isoformat(), today.isoformat()
        elif idx == 1:  # Вчера
            yesterday = today - datetime.timedelta(days=1)
            return yesterday.isoformat(), yesterday.isoformat()
        elif idx == 2:  # Последние 7 дней
            start = today - datetime.timedelta(days=6)
            return start.isoformat(), today.isoformat()
        elif idx == 3:  # Последние 30 дней
            start = today - datetime.timedelta(days=29)
            return start.isoformat(), today.isoformat()
        else:  # Текущий месяц
            start = today.replace(day=1)
            return start.isoformat(), today.isoformat()

    def _get_daily_data(self, start_date: str, end_date: str) -> list[dict]:
        """Получить активность с группировкой по дням."""
        conn = self.db._get_connection()
        try:
            rows = conn.execute(
                'SELECT date, app_name, SUM(duration_seconds) as duration_seconds '
                'FROM activity WHERE date >= ? AND date <= ? '
                'GROUP BY date, app_name ORDER BY date',
                (start_date, end_date)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _build_chart(self):
        """Построить столбчатую диаграмму."""
        start_date, end_date = self._get_date_range()
        logger.debug(f'Построение графика за период: {start_date} — {end_date}')

        # Получаем агрегированные данные по приложениям за период
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

        # Берём топ-10 приложений, остальные в "Прочее"
        activity.sort(key=lambda x: x['duration_seconds'], reverse=True)
        top = activity[:10]
        other_seconds = sum(x['duration_seconds'] for x in activity[10:])

        labels = []
        values = []
        colors = []

        for i, item in enumerate(top):
            labels.append(item['app_name'])
            values.append(item['duration_seconds'] / 60)  # в минутах
            colors.append(COLORS[i % len(COLORS)])

        if other_seconds > 0:
            labels.append('Прочее')
            values.append(other_seconds / 60)
            colors.append(COLORS[-1])

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
        ax.set_title(f'Активность приложений\n{start_date} — {end_date}', fontsize=12, fontweight='bold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.grid(True, alpha=0.3)

        self.canvas.draw()
