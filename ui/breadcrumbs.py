import os


def _component_path() -> str:
    """Вернуть путь к файлу, вызвавшему эту функцию, относительно корня проекта."""
    import inspect
    frame = inspect.currentframe()
    # Поднимаемся на 2 фрейма: _component_path -> вызывающая функция -> init
    f_back = frame.f_back if frame else None
    caller_frame = f_back.f_back if f_back else None
    caller_file = caller_frame.f_globals.get('__file__', '') if caller_frame else ''
    return _rel_path(caller_file)


def _rel_path(abspath: str) -> str:
    """Преобразовать абсолютный путь в относительный от корня проекта."""
    if not abspath:
        return ''
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        return os.path.relpath(abspath, project_root)
    except ValueError:
        return abspath


def breadcrumb_title(display_name: str) -> str:
    """Сформировать заголовок окна в формате: путь/к/файлу.py › display_name"""
    path = _component_path()
    if path:
        return f'{path} › {display_name}'
    return display_name


def component_tooltip(obj: object) -> str:
    """Вернуть путь к файлу, где определён класс объекта, относительно корня проекта.
    Использовать: widget.setToolTip(component_tooltip(self))
    """
    module = type(obj).__module__
    # Преобразуем модуль в путь к файлу
    file_path = module.replace('.', os.sep) + '.py'
    return file_path
