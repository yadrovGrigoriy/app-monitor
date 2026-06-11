# План рефакторинга архитектуры AppMonitor

## Цель

Привести структуру проекта в соответствие с `GLOSSARY.md` — разделить на логические блоки:

| Блок | Описание | Приложение |
|------|----------|------------|
| **M** (Monitor) | Ядро мониторинга — опрос окон, БД, лимиты | AppMonitor.exe |
| **MUI** (Monitor UI) | Десктопный интерфейс PyQt5 | AppMonitor.exe |
| **MWS** (Monitor Web Server) | Веб-сервер FastAPI для удалённого доступа | AppMonitor.exe |
| **AUI** (Admin UI) | Интерфейс администратора (отдельное приложение) | AppMonitorAdmin.exe |
| **UPD** (Updater) | Модуль обновления (клиент + сервер раздачи) | AppMonitorAdmin.exe |

## Текущая структура (до рефакторинга)

```
AppMonitor/
├── main.py                  # Точка входа (M + MUI + MWS)
├── run_app.py               # Точка входа (M + MUI + MWS)
├── run_admin.py             # Точка входа (AUI + UPD)
├── run_server.py            # Точка входа (только MWS)
├── core/                    # M — ядро мониторинга
│   ├── database.py
│   ├── monitor.py
│   ├── limiter.py
│   ├── scheduler.py
│   ├── reporter.py
│   ├── auth.py
│   ├── role_manager.py
│   ├── self_protect.py
│   ├── autostart.py
│   ├── notifier.py          # ⚠️ Зависит от PyQt5 — не место в core
│   └── updater.py           # ⚠️ Должен быть в UPD
├── ui/                      # MUI — десктопный интерфейс
│   ├── app_ui.py
│   ├── admin_ui.py          # ⚠️ Должен быть в AUI
│   ├── base_ui.py
│   ├── main_window.py
│   ├── styles.py
│   ├── theme_manager.py
│   ├── tray_manager.py
│   ├── app_icon.py
│   ├── dialogs/
│   │   ├── auth_dialogs.py
│   │   ├── limit_dialog.py
│   │   ├── settings_dialog.py
│   │   ├── stats_dialog.py
│   │   └── update_dialog.py # ⚠️ Должен быть в UPD
│   └── widgets/
│       ├── activity_table.py
│       ├── bottom_bar.py
│       ├── date_toolbar.py
│       ├── status_bar.py
│       └── tracked_table.py
├── api/                     # MWS — веб-сервер
│   ├── server.py
│   ├── admin_server.py      # ⚠️ Должен быть в UPD/AUI
│   └── schemas.py
├── client/                  # (пусто)
├── updater/                 # (пусто)
├── tests/
│   ├── conftest.py
│   └── ui/
│       ├── test_main_window.py
│       ├── test_admin_integration.py
│       ├── test_auth_dialogs.py
│       ├── test_auth_flow.py
│       ├── test_limit_dialog.py
│       ├── test_settings_dialog.py
│       ├── test_stats_dialog.py
│       └── test_tracked_table.py
├── data/
├── logs/
├── AppMonitor.spec           # PyInstaller spec для AppMonitor.exe
├── AppMonitorAdmin.spec      # PyInstaller spec для AppMonitorAdmin.exe
└── pyproject.toml
```

## Целевая структура (после рефакторинга)

```
AppMonitor/
├── main.py                  # Точка входа (M + MUI + MWS) — алиас run_app.py
├── run_app.py               # Точка входа (M + MUI + MWS)
├── run_admin.py             # Точка входа (AUI + UPD)
├── run_server.py            # Точка входа (только MWS)
│
├── core/                    # M — ядро мониторинга (без GUI-зависимостей)
│   ├── __init__.py
│   ├── database.py          # SQLite БД
│   ├── monitor.py           # ActivityMonitor
│   ├── limiter.py           # Принудительное закрытие
│   ├── scheduler.py         # Планировщик
│   ├── reporter.py          # Email-отчёты
│   ├── auth.py              # Аутентификация
│   ├── role_manager.py      # Роли
│   ├── self_protect.py      # Самозащита
│   ├── autostart.py         # Автозагрузка
│   └── logger.py            # Логирование
│
├── ui/                      # MUI — десктопный интерфейс PyQt5
│   ├── __init__.py
│   ├── app_ui.py            # Главное окно пользователя
│   ├── base_ui.py           # Базовый класс UI
│   ├── main_window.py       # Основное окно с вкладками
│   ├── styles.py            # CSS-стили
│   ├── theme_manager.py     # Управление темой
│   ├── tray_manager.py      # Иконка в трее
│   ├── app_icon.py          # Генерация иконок
│   ├── notifier.py          # ← из core/notifier.py (зависит от PyQt5)
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── auth_dialogs.py
│   │   ├── limit_dialog.py
│   │   ├── settings_dialog.py
│   │   └── stats_dialog.py
│   └── widgets/
│       ├── __init__.py
│       ├── activity_table.py
│       ├── bottom_bar.py
│       ├── date_toolbar.py
│       ├── status_bar.py
│       └── tracked_table.py
│
├── api/                     # MWS — веб-сервер FastAPI
│   ├── __init__.py
│   ├── server.py            # AppMonitorAPI
│   └── schemas.py           # Pydantic схемы
│
├── client/                  # AUI — клиент администрирования
│   ├── __init__.py
│   ├── admin_ui.py          # ← из ui/admin_ui.py
│   ├── admin_client.py      # ← AdminClient из admin_ui.py (выделен)
│   └── admin_server.py      # ← из api/admin_server.py (сервер раздачи обновлений)
│
├── updater/                 # UPD — модуль обновления
│   ├── __init__.py
│   ├── updater.py           # ← из core/updater.py
│   └── update_dialog.py     # ← из ui/dialogs/update_dialog.py
│
├── tests/
│   ├── conftest.py
│   ├── core/                # Тесты для core (будущие)
│   ├── ui/                  # Тесты для MUI
│   │   ├── test_main_window.py
│   │   ├── test_auth_dialogs.py
│   │   ├── test_auth_flow.py
│   │   ├── test_limit_dialog.py
│   │   ├── test_settings_dialog.py
│   │   ├── test_stats_dialog.py
│   │   └── test_tracked_table.py
│   ├── client/              # Тесты для AUI (будущие)
│   │   └── test_admin_integration.py
│   └── updater/             # Тесты для UPD (будущие)
│
├── data/
├── logs/
├── AppMonitor.spec
├── AppMonitorAdmin.spec
├── GLOSSARY.md
├── AGENTS.md
├── REFACTORING_PLAN.md      # ← этот файл
└── pyproject.toml
```

## Пошаговый план изменений

### Шаг 1. Создать новые директории и переместить файлы

| № | Действие | Файл | Из | В |
|---|----------|------|----|---|
| 1 | move | `core/updater.py` | `core/` | `updater/updater.py` |
| 2 | move | `ui/dialogs/update_dialog.py` | `ui/dialogs/` | `updater/update_dialog.py` |
| 3 | move | `core/notifier.py` | `core/` | `ui/notifier.py` |
| 4 | move | `ui/admin_ui.py` | `ui/` | `client/admin_ui.py` |
| 5 | move | `api/admin_server.py` | `api/` | `client/admin_server.py` |
| 6 | extract | AdminClient из `admin_ui.py` | — | `client/admin_client.py` |

### Шаг 2. Обновить импорты во всех файлах

| № | Файл | Что меняется |
|---|------|-------------|
| 1 | `run_admin.py` | `from ui.admin_ui` → `from client.admin_ui`; `from api.admin_server` → `from client.admin_server`; `from core.updater` → `from updater.updater`; `from ui.dialogs.update_dialog` → `from updater.update_dialog` |
| 2 | `run_app.py` | `from core.updater` → удалить (проверка обновлений теперь в AUI) |
| 3 | `main.py` | `from core.updater` → удалить |
| 4 | `ui/app_ui.py` | `from core.notifier` → `from ui.notifier` |
| 5 | `ui/tray_manager.py` | `from core.notifier` → `from ui.notifier` |
| 6 | `ui/base_ui.py` | удалить импорт `admin_ui` (если есть) |
| 7 | `updater/update_dialog.py` | `from core.updater` → `from updater.updater` |
| 8 | `updater/updater.py` | `from core.logger` → остаётся (логгер — общий для всех) |
| 9 | `client/admin_server.py` | без изменений (импортирует только core.logger) |
| 10 | `client/admin_ui.py` | `from ui.base_ui` → остаётся (BaseUI — общий); `from api.admin_server` → `from client.admin_server` |
| 11 | `tests/ui/test_admin_integration.py` | `from ui.admin_ui` → `from client.admin_ui` |
| 12 | `tests/ui/test_main_window.py` | без изменений |

### Шаг 3. Обновить spec-файлы PyInstaller

| № | Файл | Что меняется |
|---|------|-------------|
| 1 | `AppMonitor.spec` | `hiddenimports` — убрать `updater`, `client.admin_server`; добавить `ui.notifier` |
| 2 | `AppMonitorAdmin.spec` | `hiddenimports` — добавить `updater`, `client.admin_server`, `client.admin_ui` |

### Шаг 4. Обновить AGENTS.md

Отразить новую структуру директорий в документации.

### Шаг 5. Проверить и запустить тесты

```bash
pytest tests/ -v
```

## Примечания

- **core/notifier.py** → **ui/notifier.py**: Notifier использует `QSystemTrayIcon` и `QMessageBox` из PyQt5, что нарушает принцип изоляции ядра от GUI. Перенос в `ui/` решает эту проблему.
- **updater/updater.py** остаётся без PyQt5-зависимостей (использует только `urllib`), поэтому может использоваться и в `run_app.py` при необходимости.
- **client/admin_client.py** выделяется из `admin_ui.py` для разделения HTTP-клиента и UI-логики.
- **BaseUI** остаётся в `ui/` — он используется и AppUI, и AdminUI (через наследование). AdminUI импортирует его из `ui.base_ui`.
