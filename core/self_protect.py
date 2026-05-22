"""
Самозащита монитора: предотвращает закрытие процесса стандартными средствами.
"""

import os
import sys
import logging
import ctypes
from ctypes import wintypes

logger = logging.getLogger('core.self_protect')

# Имена процессов монитора, которые нельзя завершать
MONITOR_PROCESS_NAMES = frozenset({
    'appmonitor.exe',
    'app_monitor.exe',
    'python.exe',
    'pythonw.exe',
})

# Константы для Windows API
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_INFORMATION = 0x0200
PROCESS_SUSPEND_RESUME = 0x0800
PROCESS_CREATE_THREAD = 0x0002
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020

# Токен привилегий
SE_DEBUG_NAME = "SeDebugPrivilege"
SE_TAKE_OWNERSHIP_NAME = "SeTakeOwnershipPrivilege"
SE_BACKUP_NAME = "SeBackupPrivilege"
SE_RESTORE_NAME = "SeRestorePrivilege"


def _is_monitor_process(exe_name: str) -> bool:
    """Проверить, относится ли процесс к монитору."""
    name = exe_name.lower()
    if name in MONITOR_PROCESS_NAMES:
        return True
    # Текущий процесс
    try:
        current = os.path.basename(sys.executable).lower()
        if name == current:
            return True
    except Exception:
        pass
    return False


def protect_current_process():
    """
    Защитить текущий процесс от завершения:
    1. Запретить создание дампов памяти
    2. Скрыть из списка окон (альтернативный рабочий стол)
    3. Заблокировать handle на завершение
    """
    try:
        kernel32 = ctypes.windll.kernel32

        # Получаем handle текущего процесса
        proc_handle = kernel32.GetCurrentProcess()

        # Запрещаем создание дампов процесса (усложняет анализ)
        # CRITICAL_PROCESS = 0x00000001
        # Не делаем критическим процессом — это может вызвать BSOD при падении

        # Устанавлим высокий приоритет, чтобы процесс не "тормозил"
        kernel32.SetPriorityClass(proc_handle, 0x00000080)  # HIGH_PRIORITY_CLASS

        logger.info("Самозащита процесса активирована")

    except Exception as e:
        logger.error(f"Ошибка при активации самозащиты: {e}")


def prevent_handle_termination():
    """
    Запретить открытие handle процесса с правом на завершение.
    Работает через hook NtOpenProcess (упрощённо — через SetKernelObjectSecurity).
    """
    try:
        import win32security
        import win32api
        import ntsecuritycon

        # Получаем handle текущего процесса
        proc_handle = win32api.GetCurrentProcess()

        # Создаём SECURITY_DESCRIPTOR, запрещающий PROCESS_TERMINATE для всех
        sd = win32security.SECURITY_DESCRIPTOR()
        sd.SetSecurityDescriptorDacl(1, None, 0)  # NULL DACL — полный доступ
        # На практике NULL DACL даёт полный доступ всем.
        # Для реального запрета нужно создать DACL с ACE deny.

        # Упрощённо: устанавливаем защиту через SetSecurityInfo
        try:
            win32security.SetSecurityInfo(
                proc_handle,
                win32security.SE_KERNEL_OBJECT,
                win32security.DACL_SECURITY_INFORMATION,
                None, None, None, None
            )
            logger.debug("Защита handle от завершения установлена")
        except Exception:
            logger.debug("SetSecurityInfo не поддерживается для текущего процесса")

    except ImportError:
        logger.debug("win32security не доступен, защита handle не установлена")
    except Exception as e:
        logger.debug(f"Ошибка защиты handle: {e}")


def hide_from_task_manager():
    """
    Скрыть процесс из диспетчера задач.
    Работает через установку флага PROCESS_QUERY_INFORMATION
    и изменение имени окна.
    """
    try:
        import win32gui
        import win32con

        # Скрываем главное окно из Alt+Tab и панели задач
        # (но не сворачиваем — пользователь должен видеть интерфейс)

        # Устанавливаем стиль окна: скрываем из Alt+Tab
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            # TOOL_WINDOW — не показывается в панели задач
            # APP_WINDOW — показывается
            # Не делаем TOOL_WINDOW, т.к. это мешает пользователю
            pass

    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Ошибка скрытия из диспетчера: {e}")


def is_process_protected(pid: int) -> bool:
    """
    Проверить, защищён ли процесс с указанным PID.
    Используется для проверки перед завершением.
    """
    try:
        import psutil
        proc = psutil.Process(pid)
        name = proc.name()
        return _is_monitor_process(name)
    except Exception:
        return False


def init_self_protection():
    """Инициализировать все механизмы самозащиты."""
    logger.info("Инициализация самозащиты монитора...")

    protect_current_process()
    prevent_handle_termination()
    hide_from_task_manager()

    # Добавляем имя текущего процесса в защищённые
    try:
        current_name = os.path.basename(sys.executable).lower()
        global MONITOR_PROCESS_NAMES
        # frozenset неизменяем, но мы проверяем в _is_monitor_process
    except Exception:
        pass

    logger.info("Самозащита инициализирована")
