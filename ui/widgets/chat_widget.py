import datetime
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
    QApplication,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

from core.database import Database
from core.logger import setup_logger

logger = setup_logger('ui.chat_widget')

# Цвета для сообщений
COLOR_ADMIN_BG = "#e3f2fd"      # светло-голубой — админ
COLOR_USER_BG = "#e8f5e9"       # светло-зелёный — пользователь
COLOR_ADMIN_LABEL = "#1565c0"
COLOR_USER_LABEL = "#2e7d32"
COLOR_TIME = "#757575"
COLOR_OWN_MSG = "#dcf8c6"       # зелёный как в мессенджерах


class MessageBubble(QFrame):
    """Виджет одного сообщения в чате."""

    def __init__(self, text: str, sender: str, created_at: str, is_own: bool = False):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
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
        header.addStretch()

        layout.addLayout(header)

        # Текст сообщения
        text_label = QLabel(text)
        text_label.setFont(QFont('Segoe UI', 10))
        text_label.setWordWrap(True)
        text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        text_label.setMinimumWidth(200)
        text_label.setMaximumWidth(500)
        layout.addWidget(text_label)

        # Цвет фона
        if is_own:
            bg_color = COLOR_OWN_MSG
        elif sender == 'admin':
            bg_color = COLOR_ADMIN_BG
        else:
            bg_color = COLOR_USER_BG
        self.setStyleSheet(f"""
            MessageBubble {{
                background-color: {bg_color};
                border-radius: 8px;
                margin: 2px 8px;
            }}
        """)


class ChatWidget(QWidget):
    """Виджет чата для клиента AppMonitor."""

    POLL_INTERVAL_MS = 5000  # опрос новых сообщений каждые 5 сек

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._known_ids: set[int] = set()
        self._init_ui()
        self._load_history()
        self._start_polling()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        # Заголовок
        title = QLabel('Чат с администратором')
        title.setFont(QFont('Segoe UI', 14, QFont.Bold))
        title.setStyleSheet('color: #fff;')
        layout.addWidget(title)

        desc = QLabel(
            'Здесь отображаются сообщения от администратора. '
            'Вы можете отвечать на них.'
        )
        desc.setFont(QFont('Segoe UI', 10))
        desc.setStyleSheet('color: rgba(255,255,255,.55);')
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Область сообщений (скролл)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid rgba(255,255,255,.08);
                border-radius: 8px;
                background: #1a1a2e;
            }
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
        self.input_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid rgba(255,255,255,.12);
                border-radius: 8px;
                padding: 8px;
                background: #16213e;
                color: #e0e0e0;
                selection-background-color: #6366f1;
            }
        """)
        input_layout.addWidget(self.input_edit, stretch=1)

        self.send_btn = QPushButton('Отправить')
        self.send_btn.setFont(QFont('Segoe UI', 10, QFont.Bold))
        self.send_btn.setFixedHeight(40)
        self.send_btn.setFixedWidth(120)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
            QPushButton:pressed {
                background-color: #4338ca;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #9ca3af;
            }
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
