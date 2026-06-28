"""
ChatWidget — виджет чата для клиента AppMonitor.
Адаптирован под светлую тему приложения.
"""

import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

from core.database import Database
from core.logger import setup_logger

logger = setup_logger('ui.chat_widget')

# Цвета для светлой темы
COLOR_ADMIN_BG = "#e3f2fd"       # светло-голубой — админ
COLOR_USER_BG = "#e8f5e9"        # светло-зелёный — пользователь
COLOR_OWN_MSG = "#dcf8c6"        # зелёный как в мессенджерах
COLOR_ADMIN_LABEL = "#1565c0"
COLOR_USER_LABEL = "#2e7d32"
COLOR_TIME = "#888888"
COLOR_BORDER = "#d0d0d0"
COLOR_BG = "#ffffff"
COLOR_TEXT = "#222222"
COLOR_TEXT_SECONDARY = "#666666"
COLOR_INPUT_BG = "#f5f5f5"
COLOR_BTN_BG = "#4f46e5"
COLOR_BTN_HOVER = "#4338ca"
COLOR_BTN_PRESSED = "#3730a3"
COLOR_BTN_DISABLED = "#a5b4fc"
COLOR_SCROLL_BG = "#f0f0f0"


class MessageBubble(QFrame):
    """Виджет одного сообщения в чате.

    Свои сообщения (is_own=True) выравниваются вправо,
    чужие (is_own=False) — влево.
    """

    def __init__(self, text: str, sender: str, created_at: str, is_own: bool = False, is_read: bool = True):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Внешний layout для выравнивания
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)

        # Контейнер самого сообщения
        container = QFrame()
        container.setFrameShape(QFrame.StyledPanel)
        container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        container.setMaximumWidth(500)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        # Заголовок: отправитель + время
        header = QHBoxLayout()
        header.setSpacing(8)

        sender_label = QLabel('Администратор' if sender == 'admin' else 'Вы')
        sender_label.setFont(QFont('Segoe UI', 9, QFont.Bold))
        sender_label.setStyleSheet(
            f'color: {COLOR_ADMIN_LABEL if sender == "admin" else COLOR_USER_LABEL};'
        )
        header.addWidget(sender_label)

        try:
            dt = datetime.datetime.fromisoformat(created_at)
            time_str = dt.strftime('%H:%M')
        except (ValueError, TypeError):
            time_str = ''
        time_label = QLabel(time_str)
        time_label.setFont(QFont('Segoe UI', 8))
        time_label.setStyleSheet(f'color: {COLOR_TIME};')
        header.addWidget(time_label)

        # Статус прочтения (только для своих сообщений)
        if is_own:
            status_text = 'прочитано' if is_read else 'отправлено'
            status_color = '#4caf50' if is_read else COLOR_TIME
            status_label = QLabel(status_text)
            status_label.setFont(QFont('Segoe UI', 8))
            status_label.setStyleSheet(f'color: {status_color};')
            header.addWidget(status_label)

        header.addStretch()

        layout.addLayout(header)

        # Текст сообщения
        text_label = QLabel(text)
        text_label.setFont(QFont('Segoe UI', 10))
        text_label.setWordWrap(True)
        text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        text_label.setMinimumWidth(200)
        layout.addWidget(text_label)

        # Цвет фона
        if is_own:
            bg_color = COLOR_OWN_MSG
        elif sender == 'admin':
            bg_color = COLOR_ADMIN_BG
        else:
            bg_color = COLOR_USER_BG
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
            }}
        """)

        # Выравнивание: свои — справа, чужие — слева
        if is_own:
            outer.addStretch()
            outer.addWidget(container)
        else:
            outer.addWidget(container)
            outer.addStretch()


class ChatWidget(QWidget):
    """Виджет чата для клиента AppMonitor (светлая тема)."""

    POLL_INTERVAL_MS = 5000  # опрос новых сообщений каждые 5 сек

    # Сигнал: новое сообщение от администратора (текст, id)
    new_admin_message = pyqtSignal(str, int)

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._known_ids: set[int] = set()
        self._init_ui()
        self._load_history()
        self._start_polling()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        # Заголовок
        title = QLabel('Чат с администратором')
        title.setFont(QFont('Segoe UI', 14, QFont.Bold))
        title.setStyleSheet(f'color: {COLOR_TEXT};')
        layout.addWidget(title)

        desc = QLabel(
            'Здесь отображаются сообщения от администратора. '
            'Вы можете отвечать на них.'
        )
        desc.setFont(QFont('Segoe UI', 10))
        desc.setStyleSheet(f'color: {COLOR_TEXT_SECONDARY};')
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Область сообщений (скролл)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {COLOR_SCROLL_BG};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #c0c0c0;
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.setSpacing(6)
        self.messages_layout.setContentsMargins(8, 8, 8, 8)
        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area, stretch=1)

        # Поле ввода и кнопка отправки
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText('Напишите ответ администратору...')
        self.input_edit.setMaximumHeight(80)
        self.input_edit.setFont(QFont('Segoe UI', 10))
        self.input_edit.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 8px;
                background: {COLOR_INPUT_BG};
                color: {COLOR_TEXT};
                selection-background-color: #c7d2fe;
            }}
        """)
        input_layout.addWidget(self.input_edit, stretch=1)

        self.send_btn = QPushButton('Отправить')
        self.send_btn.setFont(QFont('Segoe UI', 10, QFont.Bold))
        self.send_btn.setFixedHeight(40)
        self.send_btn.setFixedWidth(120)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_BTN_BG};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_BTN_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_BTN_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BTN_DISABLED};
                color: #e0e0e0;
            }}
        """)
        self.send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

    def _load_history(self):
        """Загрузить историю сообщений из БД."""
        try:
            history = self.db.get_message_history(100)
            self._known_ids.clear()
            for msg in history:
                self._add_message_bubble(msg, is_own=(msg['sender'] == 'user'))
                self._known_ids.add(msg['id'])
            self._scroll_to_bottom()
            logger.debug(f'Загружено {len(history)} сообщений из истории')
        except Exception as e:
            logger.error(f'Ошибка загрузки истории сообщений: {e}')

    def _add_message_bubble(self, msg: dict, is_own: bool = False):
        """Добавить пузырёк сообщения в ленту."""
        bubble = MessageBubble(
            text=msg['text'],
            sender=msg['sender'],
            created_at=msg['created_at'],
            is_own=is_own,
            is_read=msg.get('is_read', True),
        )
        self.messages_layout.addWidget(bubble)

    def _scroll_to_bottom(self):
        """Прокрутить скролл вниз."""
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def _start_polling(self):
        """Запустить таймер опроса новых сообщений."""
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_new_messages)
        self._poll_timer.start(self.POLL_INTERVAL_MS)

    def _poll_new_messages(self):
        """Проверить новые сообщения от администратора."""
        try:
            pending = self.db.get_pending_messages()
            for msg in pending:
                if msg['id'] not in self._known_ids:
                    self._add_message_bubble(msg, is_own=False)
                    self._known_ids.add(msg['id'])
                    # Отмечаем как прочитанное
                    self.db.mark_message_as_read(msg['id'])
                    # Испускаем сигнал для уведомления
                    self.new_admin_message.emit(msg['text'], msg['id'])
            if pending:
                self._scroll_to_bottom()
        except Exception as e:
            logger.error(f'Ошибка опроса сообщений: {e}')

    def _send_message(self):
        """Отправить ответ администратору."""
        text = self.input_edit.toPlainText().strip()
        if not text:
            return

        try:
            msg = self.db.add_message(text, 'user')
            self._add_message_bubble(msg, is_own=True)
            self._known_ids.add(msg['id'])
            self.input_edit.clear()
            self._scroll_to_bottom()
            logger.info(f'Ответ отправлен: {text[:50]}...')
        except Exception as e:
            logger.error(f'Ошибка отправки сообщения: {e}')

    def cleanup(self):
        """Остановить таймер при закрытии."""
        if hasattr(self, '_poll_timer') and self._poll_timer:
            self._poll_timer.stop()
