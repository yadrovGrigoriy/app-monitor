"""Диалоги добавления и редактирования лимита для приложения."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QPushButton, QComboBox, QCheckBox, QMessageBox,
)
from PyQt5.QtCore import Qt
from core.database import Database
from ui.styles import GLOBAL_STYLE
from ui.breadcrumbs import breadcrumb_title, component_tooltip


class AddLimitDialog(QDialog):
    """Диалог выбора приложения и установки лимита."""

    def __init__(self, db: Database, parent=None, preset_app: str = '',
                 title: str = 'Новый лимит', label: str = 'Выберите приложение:'):
        super().__init__(parent)
        self.db = db
        self.app_name = preset_app
        self.limit_minutes = 60
        self.setWindowTitle(breadcrumb_title(title))
        self.setToolTip(component_tooltip(self))
        self.setFixedSize(380, 200)
        self.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title_label = QLabel(label)
        title_label_font = title_label.font()
        title_label_font.setBold(True)
        title_label.setFont(title_label_font)
        layout.addWidget(title_label)

        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QComboBox.NoInsert)
        self.combo.setStyleSheet('''
            QComboBox {
                padding: 6px 10px;
                border-radius: 6px;
                border: 1px solid #c0c0c0;
                min-height: 24px;
            }
            QComboBox:focus {
                border-color: #0078d4;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #c0c0c0;
            }
            QComboBox QAbstractItemView {
                border-radius: 6px;
                padding: 4px;
            }
        ''')
        self._load_apps()
        if preset_app:
            idx = self.combo.findText(preset_app, Qt.MatchFlag.MatchContains)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)
        layout.addWidget(self.combo)

        layout.addWidget(QLabel('Лимит:'))

        time_layout = QHBoxLayout()
        time_layout.setSpacing(6)

        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 24)
        self.hours_spin.setValue(1)
        self.hours_spin.setSuffix(' ч')
        self.hours_spin.setFixedWidth(80)
        time_layout.addWidget(self.hours_spin)

        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(0)
        self.minutes_spin.setSuffix(' мин')
        self.minutes_spin.setFixedWidth(80)
        time_layout.addWidget(self.minutes_spin)

        time_layout.addStretch()
        layout.addLayout(time_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton('Добавить')
        btn_ok.setFixedHeight(32)
        btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.setFixedHeight(32)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _load_apps(self):
        """Заполнить список приложениями из БД."""
        apps = {}  # app_name -> пример заголовка окна
        # Из текущей активности
        for a in self.db.get_today_activity():
            if a['app_name'] not in apps:
                apps[a['app_name']] = a.get('window_title', '')
        # Из уже установленных лимитов
        for l in self.db.get_all_limits():
            if l['app_name'] not in apps:
                apps[l['app_name']] = ''

        # Сортируем и добавляем в комбобокс
        for name in sorted(apps.keys()):
            title = apps[name]
            if title:
                display = f'{name} — {title[:50]}'
            else:
                display = name
            self.combo.addItem(display, userData=name)

    def _on_ok(self):
        name = self.combo.currentData()
        if not name:
            text = self.combo.currentText().strip()
            if ' — ' in text:
                name = text.split(' — ')[0]
            else:
                name = text
        if not name:
            QMessageBox.warning(self, 'Ошибка', 'Введите имя приложения')
            return
        self.app_name = name
        self.limit_minutes = self.hours_spin.value() * 60 + self.minutes_spin.value()
        if self.limit_minutes < 1:
            QMessageBox.warning(self, 'Ошибка', 'Лимит должен быть хотя бы 1 минута')
            return
        self.accept()


class EditLimitDialog(QDialog):
    """Диалог редактирования существующего лимита."""

    def __init__(self, db: Database, limit_data: dict, parent=None):
        super().__init__(parent)
        self.db = db
        self.app_name = limit_data['app_name']
        self.limit_minutes = limit_data['limit_minutes']
        self.enabled = bool(limit_data['enabled'])

        self.setWindowTitle(breadcrumb_title(f'Редактировать: {self.app_name}'))
        self.setToolTip(component_tooltip(self))
        self.setFixedSize(360, 240)
        self.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel(f'Редактирование лимита: {self.app_name}')
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addWidget(QLabel('Лимит:'))

        time_layout = QHBoxLayout()
        time_layout.setSpacing(6)

        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 24)
        self.hours_spin.setValue(self.limit_minutes // 60)
        self.hours_spin.setSuffix(' ч')
        self.hours_spin.setFixedWidth(80)
        time_layout.addWidget(self.hours_spin)

        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(self.limit_minutes % 60)
        self.minutes_spin.setSuffix(' мин')
        self.minutes_spin.setFixedWidth(80)
        time_layout.addWidget(self.minutes_spin)

        time_layout.addStretch()
        layout.addLayout(time_layout)

        self.enabled_check = QCheckBox('Лимит включён')
        self.enabled_check.setChecked(self.enabled)
        layout.addWidget(self.enabled_check)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save = QPushButton('Сохранить')
        btn_save.setFixedHeight(32)
        btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_save)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.setFixedHeight(32)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _on_save(self):
        new_minutes = self.hours_spin.value() * 60 + self.minutes_spin.value()
        if new_minutes < 1:
            QMessageBox.warning(self, 'Ошибка', 'Лимит должен быть хотя бы 1 минута')
            return
        self.limit_minutes = new_minutes
        self.enabled = self.enabled_check.isChecked()
        self.db.set_limit(self.app_name, self.limit_minutes, self.enabled)
        self.accept()
