"""Диалоги авторизации и регистрации администратора."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ui.styles import global_style, COLOR_DANGER


class AddAdminDialog(QDialog):
    """Диалог добавления нового администратора."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Добавить администратора')
        self.setFixedSize(400, 280)
        self.setStyleSheet(global_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel('Новый администратор')
        title_font = QFont('Segoe UI', 12, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addWidget(QLabel('Придумайте логин и пароль для нового администратора:'))

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Логин')
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('Пароль')
        layout.addWidget(self.password_input)

        self.password_confirm = QLineEdit()
        self.password_confirm.setEchoMode(QLineEdit.Password)
        self.password_confirm.setPlaceholderText('Повторите пароль')
        layout.addWidget(self.password_confirm)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton('Добавить')
        btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _on_ok(self):
        if not self.username_input.text().strip():
            QMessageBox.warning(self, 'Ошибка', 'Введите логин')
            return
        if not self.password_input.text():
            QMessageBox.warning(self, 'Ошибка', 'Введите пароль')
            return
        if self.password_input.text() != self.password_confirm.text():
            QMessageBox.warning(self, 'Ошибка', 'Пароли не совпадают')
            return
        self.accept()


class AuthDialog(QDialog):
    """Диалог входа администратора."""

    def __init__(self, parent=None, attempt: int = 0):
        super().__init__(parent)
        self.setWindowTitle('Вход')
        # self.setFixedSize(240, 180)
        self.setStyleSheet(global_style())
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        if attempt > 0:
            hint = QLabel(f'Попытка {attempt + 1} из 3')
            hint.setStyleSheet(f'color: {COLOR_DANGER};')
            layout.addWidget(hint)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Логин')
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('Пароль')
        layout.addWidget(self.password_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton('Войти')
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)


class RegisterDialog(QDialog):
    """Диалог создания администратора."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Регистрация')
        self.setFixedSize(400, 300)
        self.setStyleSheet(global_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel('Создание администратора')
        title_font = QFont('Segoe UI', 12, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addWidget(QLabel('Придумайте логин и пароль для управления настройками:'))

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Логин')
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('Пароль')
        layout.addWidget(self.password_input)

        self.password_confirm = QLineEdit()
        self.password_confirm.setEchoMode(QLineEdit.Password)
        self.password_confirm.setPlaceholderText('Повторите пароль')
        layout.addWidget(self.password_confirm)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton('Создать')
        btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _on_ok(self):
        if not self.username_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите логин")
            return
        if not self.password_input.text():
            QMessageBox.warning(self, "Ошибка", "Введите пароль")
            return
        if self.password_input.text() != self.password_confirm.text():
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return
        self.accept()
