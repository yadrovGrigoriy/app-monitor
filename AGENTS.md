# AGENTS.md — Руководство для контрибьюторов AppMonitor

## Структура проекта и организация модулей

```
AppMonitor/
├── main.py                  # Точка входа приложения
├── requirements.txt         # Зависимости
├── api/                     # FastAPI сервер для удалённого доступа
│   ├── server.py            # AppMonitorAPI — FastAPI приложение
│   └── schemas.py           # Pydantic схемы запросов/ответов
├── client/                  # Отдельное клиентское приложение (HTTP)
│   └── main.py
├── core/                    # Ядро приложения
│   ├── database.py          # SQLite БД (таблицы, миграции, CRUD)
│   ├── monitor.py           # ActivityMonitor — опрос активных окон
│   ├── auth.py              # AuthManager — аутентификация (SHA-256 + соль)
│   ├── role_manager.py      # Роли: admin / user
│   ├── limiter.py           # Принудительное закрытие приложений
│   ├── notifier.py          # Уведомления (трей / QMessageBox)
│   ├── reporter.py          # Email-отчёты (SMTP)
│   ├── scheduler.py         # Ежедневный планировщик (schedule)
│   ├── autostart.py         # Автозагрузка через реестр Windows
│   ├── self_protect.py      # Самозащита процесса
│   └── logger.py            # Настройка логирования (файл + консоль)
├── ui/                      # PyQt5 интерфейс
│   ├── app_ui.py            # Главное окно пользователя
│   ├── admin_ui.py          # Удалённый интерфейс администратора
│   ├── base_ui.py           # Базовый класс UI
│   ├── main_window.py       # Основное окно с вкладками
│   ├── styles.py            # CSS-стили
│   ├── theme_manager.py     # Управление темой (тёмная/светлая)
│   ├── tray_manager.py      # Иконка в системном трее
│   ├── breadcrumbs.py       # Навигационные хлебные крошки
│   ├── app_icon.py          # Генерация иконки приложения
│   ├── dialogs/             # Диалоговые окна
│   │   ├── auth_dialogs.py
│   │   ├── limit_dialog.py
│   │   ├── settings_dialog.py
│   │   └── stats_dialog.py
│   └── widgets/             # Переиспользуемые виджеты
│       ├── activity_table.py
│       ├── bottom_bar.py
│       ├── date_toolbar.py
│       └── tracked_table.py
├── tests/                   # Тесты
│   ├── conftest.py          # Фикстуры (временная БД, тестовые данные)
│   └── ui/                  # UI-тесты (unittest + mock)
│       ├── test_main_window.py
│       ├── test_auth_dialogs.py
│       ├── test_limit_dialog.py
│       ├── test_settings_dialog.py
│       ├── test_stats_dialog.py
│       └── test_tracked_table.py
├── data/                    # SQLite БД (app_monitor.db)
└── logs/                    # Логи (appmonitor_YYYYMMDD.log)
```

**Ключевые принципы:**
- `core/` — бизнес-логика без привязки к GUI
- `ui/` — только PyQt5, вызывает core через сигналы/слоты
- `api/` — FastAPI, работает поверх core.database
- `client/` — отдельное приложение, общается с api через HTTP

## Команды сборки, тестирования и разработки

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python main.py

# Запуск тестов
pytest tests/ -v

# Запуск конкретного теста
pytest tests/ui/test_main_window.py -v

# Запуск с логами (без подавления)
APPMONITOR_TESTING=0 pytest tests/ -v

# Запуск API-сервера отдельно
python -m uvicorn api.server:app --host 0.0.0.0 --port 8765
```

## Логирование и мониторинг ошибок

- **Логи пишутся в `logs/appmonitor_YYYYMMDD.log`** — файл на каждый день
- **Формат строки:** `ЧЧ:ММ:СС | УРОВЕНЬ | модуль | сообщение`
- **Уровни:** `DEBUG`, `INFO`, `WARNING`, `ERROR` — все пишутся и в файл, и в консоль
- **После запуска приложения** (через `python main.py` или из PyCharm) сразу просматривай логи в терминале — там видны все этапы инициализации, ошибки подключения к БД, проблемы с win32 API и т.д.
- **При падении или некорректном поведении** первым делом проверь `logs/` — там полная картина без подавления
- **В тестах** логи подавляются переменной `APPMONITOR_TESTING=1` — если нужно увидеть логи тестов, запускай с `APPMONITOR_TESTING=0`

## Стиль кода и правила именования

- **Язык:** Python 3.12+
- **Отступы:** 4 пробела
- **Строки:** двойные кавычки для docstring, одинарные для кода
- **Именование:** `snake_case` для функций/переменных, `PascalCase` для классов, `UPPER_CASE` для констант
- **Типизация:** аннотации типов обязательны для публичных методов
- **Логирование:** использовать `core.logger.setup_logger(__name__)` в каждом модуле
- **Docstrings:** русский язык, стиль PEP 257
- **Тесты:** `unittest` + `unittest.mock`, файлы `test_*.py` в `tests/ui/`
- **Фикстуры:** `tests/conftest.py` — `create_test_db()` для временной БД
- **Покрытие:** тестировать UI-диалоги через mock, core-логику через реальную БД

## Рекомендации по VCS: коммиты и пулл реквесты

**Формат коммитов (Conventional Commits):**
```
feat(core): add database layer and activity monitor
feat(ui): add main window with tray icon and settings dialog
refactor: split UI into components, native Windows 11 style
chore: remove generator scripts from repo, update .gitignore
fix: correct time display on active tab
```

**Правила:**
- Префиксы: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`
- Опциональный scope в скобках: `(core)`, `(ui)`, `(api)`
- Тело коммита — на русском или английском, единообразно
- PR должен содержать описание изменений и ссылку на issue (если есть)
- Скриншоты для UI-изменений приветствуются

## Архитектурные заметки

- **Windows-only:** приложение использует win32 API (pywin32) для мониторинга окон, автозагрузки и самозащиты
- **Одиночный экземпляр:** проверка через mutex + убийство старых процессов (psutil)
- **Самозащита:** процесс защищён от завершения через Task Manager (SetSecurityInfo)
- **Миграции БД:** автоматические в `Database._init_db()` — пересоздание таблиц с переносом данных
- **Токены:** SHA-256 + соль для паролей, случайные токены для сессий (TTL 24ч)
