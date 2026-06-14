"""Runtime hook для PyInstaller — проверка единственного экземпляра через файл блокировки.

Файл блокировки работает даже в PyInstaller GUI-заглушке, потому что
он выполняется до создания дочернего процесса.
"""
import os
import sys

LOCK_FILE = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'AppMonitor.lock')


def _check_single_instance() -> bool:
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 0)
                return False
            except OSError:
                pass
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return True


if not _check_single_instance():
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, 'Приложение AppMonitor уже запущено!', 'AppMonitor', 0)
    sys.exit(0)
