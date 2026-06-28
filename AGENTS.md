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

## Сборка для механизма обновления

Для проверки механизма обновления нужно собрать **2 компонента**:

### 1. AppMonitor.exe (клиентское приложение)
```bash
pyinstaller AppMonitor.spec --noconfirm
```
Результат: `dist/AppMonitor.exe`

### 2. Установщик AppMonitor_Setup_X.X.X.exe (раздаётся сервером обновлений)
```bash
# Требуется NSIS (Nullsoft Scriptable Install System)
# Установка: winget install NSIS.NSIS

# Сборка установщика:
"C:\Program Files (x86)\NSIS\makensis.exe" installer\installer.nsi
```
Результат: `dist/AppMonitor_Setup_X.X.X.exe`

### Полная сборка одной командой (рекомендуемый способ)
```bash
python scripts/build_all.py
```
Скрипт автоматически:
1. Генерирует `installer.nsi` из шаблона (версия из `version.txt`)
2. Собирает `AppMonitor.exe` через PyInstaller
3. Собирает установщик через NSIS и копирует в `dist/` для автообновления

### Как работает обновление

1. **AppMonitor.exe** (клиент) периодически шлёт запрос на сервер Admin UI (`https://192.168.3.27:8766/api/update/check`)
2. **Admin Server** (`api/admin_server.py`) ищет установщик в папке `dist/` по шаблону `AppMonitor_Setup_*.exe`
3. Если версия установщика новее — клиент скачивает его через `/api/update/download/{version}`
4. Клиент запускает установщик с флагом `/S /AUTORUN` (тихая установка + автозапуск) и завершает себя
5. Установщик обновляет файлы и запускает свежий `AppMonitor.exe`

**Важно:**
- Версия приложения задаётся в `core/version.py` (читается из `version.txt`)
- Версия установщика извлекается из имени файла `AppMonitor_Setup_X.X.X.exe`
- Admin Server **запускается автоматически** вместе с AdminUI (`python run_admin.py`) на порту 8766 в фоновом потоке
- Клиент (AppMonitor) обращается к серверу по адресу `https://192.168.3.27:8766`
- Сертификаты (`data/cert.pem`, `data/key.pem`) нужны для HTTPS

### Автоинкремент версии при сборке

Скрипт `scripts/build_installer.ps1` **автоматически повышает версию** при каждой сборке:
- Читает текущую версию из `version.txt`
- Увеличивает последнюю цифру (patch) на 1
- Обновляет версию в `version.txt`, `pyproject.toml` и генерирует `installer.nsi`
- Затем собирает `AppMonitor.exe` и установщик

Пример: `1.2.1` → `1.2.2` → `1.2.3`

Чтобы собрать установщик с новой версией:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1
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

## Чеклист проверок после сборки

После каждой сборки новой версии (изменения `version.txt` → `patch_nsi.py` → `build_exe.py` → `build_setup.py`) **обязательно** выполнить:

### 1. Запуск приложения
```bash
python main.py
```
- [ ] Приложение стартует без ошибок (проверить логи в терминале)
- [ ] API-сервер запускается на порту 8765
- [ ] Web UI доступен по `http://localhost:8765/web/`
- [ ] Нет `AttributeError`, `ModuleNotFoundError`, `ImportError`

### 2. Проверка версии
- [ ] В логах при старте: `Обнаружено обновление: X.X.X -> Y.Y.Y`
- [ ] В Web UI → Настройки → О системе: отображается новая версия
- [ ] `version.txt` содержит новую версию

### 3. Проверка Web UI
- [ ] Все страницы открываются (Статистика, Настройки, Чат)
- [ ] Нет ошибок `{"detail":"Not Found"}` в консоли браузера
- [ ] Нет ошибок 502 Bad Gateway
- [ ] Если добавили новый эндпоинт — проверить его через браузер или curl

### 4. Проверка обновления
- [ ] Установщик `dist/AppMonitor_Setup_X.X.X.exe` существует
- [ ] Версия установщика новее, чем текущая версия приложения
- [ ] При запуске приложения через 5-10 сек появляется уведомление об обновлении

### 5. Проверка нового функционала
- [ ] Если добавляли новый эндпоинт — проверить его работу
- [ ] Если меняли Web UI — проверить, что Vue собрался без ошибок
- [ ] Если меняли БД — проверить миграцию

### 6. Финальная сборка
- [ ] `dist/AppMonitor.exe` — существует, размер > 50 MB
- [ ] `dist/vX.X.X/AppMonitor_Setup_X.X.X.exe` — существует
- [ ] `dist/AppMonitor_Setup_X.X.X.exe` — скопирован для автообновления
