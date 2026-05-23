"""
Диалог проверки и установки обновлений AppMonitor.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit, QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor

from core.updater import (
    check_for_updates,
    download_update,
    apply_update,
    UpdateInfo,
    APP_VERSION,
)
from core.logger import setup_logger
from ui.styles import global_style

logger = setup_logger('ui.update')


class UpdateDialog(QDialog):
    """Диалог проверки и установки обновлений."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._update_info: UpdateInfo | None = None
        self._installer_path: str | None = None
        self._init_ui()
        self._start_check()

    def _init_ui(self):
        self.setWindowTitle('Проверка обновлений')
        self.setMinimumSize(520, 380)
        self.resize(560, 420)
        self.setStyleSheet(global_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Заголовок
        title = QLabel(f'AppMonitor v{APP_VERSION}')
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Статус
        self._status_label = QLabel('Проверка обновлений...')
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # Прогресс-бар (для скачивания)
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(True)
        layout.addWidget(self._progress_bar)

        # Описание релиза
        self._release_notes = QTextEdit()
        self._release_notes.setReadOnly(True)
        self._release_notes.setVisible(False)
        self._release_notes.setMaximumHeight(200)
        layout.addWidget(self._release_notes, stretch=1)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_update = QPushButton('Обновить')
        self._btn_update.setVisible(False)
        self._btn_update.clicked.connect(self._on_update_clicked)
        self._btn_update.setFixedWidth(140)
        btn_layout.addWidget(self._btn_update)

        self._btn_close = QPushButton('Закрыть')
        self._btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_close)

        layout.addLayout(btn_layout)

    def _start_check(self):
        """Запустить проверку обновлений в фоне."""
        self._status_label.setText('Проверка обновлений...')

        # Используем QTimer.singleShot для неблокирующего HTTP-запроса
        QTimer.singleShot(0, self._do_check)

    def _do_check(self):
        """Выполнить проверку (вызывается асинхронно)."""
        try:
            self._update_info = check_for_updates()
        except Exception as e:
            logger.error(f"Ошибка при проверке обновлений: {e}")
            self._update_info = None

        if self._update_info is None:
            self._status_label.setText(
                'Не удалось проверить обновления.\n'
                'Проверьте подключение к интернету.'
            )
            return

        if not self._update_info.is_newer:
            self._status_label.setText(
                f'У вас установлена последняя версия v{APP_VERSION}.'
            )
            return

        # Есть обновление
        self._status_label.setText(
            f'Доступна новая версия: '
            f'v{self._update_info.latest_version}'
        )

        self._release_notes.setVisible(True)
        self._release_notes.setPlainText(
            f'Что нового в v{self._update_info.latest_version}:\n\n'
            f'{self._update_info.release_notes}'
        )
        self._release_notes.moveCursor(QTextCursor.Start)

        self._btn_update.setVisible(True)
        self._btn_update.setEnabled(True)

    def _on_update_clicked(self):
        """Начать скачивание и установку обновления."""
        if not self._update_info:
            return

        self._btn_update.setEnabled(False)
        self._btn_update.setText('Скачивание...')
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)

        # Скачиваем в фоне
        QTimer.singleShot(0, self._do_download)

    def _do_download(self):
        """Скачать установщик."""
        try:
            self._installer_path = download_update(
                self._update_info,
                progress_callback=self._on_progress,
            )
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            self._installer_path = None

        if self._installer_path is None:
            self._status_label.setText('Ошибка скачивания обновления.')
            self._btn_update.setText('Обновить')
            self._btn_update.setEnabled(True)
            self._progress_bar.setVisible(False)
            return

        self._progress_bar.setValue(100)
        self._status_label.setText('Обновление скачано. Установить сейчас?')

        self._btn_update.setText('Установить')
        self._btn_update.setEnabled(True)
        self._btn_update.clicked.disconnect()
        self._btn_update.clicked.connect(self._do_install)

    def _on_progress(self, downloaded: int, total: int):
        """Обновить прогресс-бар."""
        if total > 0:
            percent = int(downloaded * 100 / total)
            self._progress_bar.setValue(percent)
            self._status_label.setText(
                f'Скачивание: {downloaded // 1024 // 1024} / '
                f'{total // 1024 // 1024} МБ'
            )

    def _do_install(self):
        """Запустить установку и завершить приложение."""
        if not self._installer_path:
            return

        reply = QMessageBox.question(
            self,
            'Установка обновления',
            'Приложение будет закрыто для установки обновления.\n'
            'Продолжить?',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._status_label.setText('Запуск установщика...')
        self._btn_update.setEnabled(False)
        self._btn_update.setText('Установка...')
        self.accept()

        # Запускаем установщик и завершаем процесс
        apply_update(self._installer_path)


def _check_updates_background():
    """Фоновая проверка обновлений (вызывается по таймеру).

    Если найдено обновление — показывает диалог с предложением установить.
    Если сервер недоступен — тихо пропускает.
    """
    try:
        update_info = check_for_updates()
        if update_info and update_info.is_newer:
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                None,
                'Доступно обновление',
                f'Доступна новая версия AppMonitor v{update_info.latest_version}.\n\n'
                f'{update_info.release_notes[:200]}...\n\n'
                f'Открыть диалог обновления?',
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                dialog = UpdateDialog()
                dialog.exec_()
    except Exception as e:
        logger.debug(f'Фоновая проверка обновлений: {e}')
