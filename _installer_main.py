"""
AppMonitor Installer — устанавливает монитор активности в систему.
Запуск от имени администратора.
"""
import os
import sys
import shutil
import subprocess
import ctypes
import winreg
import datetime
import traceback


LOG_FILE = None


def setup_logger():
    """Настроить логгер установщика."""
    global LOG_FILE
    try:
        log_dir = os.path.join(
            os.environ.get("ProgramData", "C:\\ProgramData"),
            "AppMonitor", "logs"
        )
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(
            log_dir,
            f"install_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        LOG_FILE = open(log_path, "w", encoding="utf-8")
        LOG_FILE.write(f"=== AppMonitor Installer ===\n")
        LOG_FILE.write(f"Start: {datetime.datetime.now()}\n")
        LOG_FILE.write(f"Python: {sys.version}\n")
        LOG_FILE.write(f"Executable: {sys.executable}\n")
        LOG_FILE.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
        LOG_FILE.write(f"MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}\n")
        LOG_FILE.write(f"Args: {sys.argv}\n")
        LOG_FILE.write(f"CWD: {os.getcwd()}\n")
        LOG_FILE.write(f"Admin: {_is_admin()}\n")
        LOG_FILE.flush()
        return log_path
    except Exception as e:
        return None


def log(msg: str):
    """Записать сообщение в лог."""
    print(msg)
    if LOG_FILE:
        try:
            LOG_FILE.write(f"{datetime.datetime.now().strftime('%H:%M:%S')} | {msg}\n")
            LOG_FILE.flush()
        except Exception:
            pass


def log_error(msg: str):
    """Записать ошибку в лог с traceback."""
    log(f"[ERROR] {msg}")
    if LOG_FILE:
        try:
            traceback.print_exc(file=LOG_FILE)
            LOG_FILE.flush()
        except Exception:
            pass




def _is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )


def create_shortcut(target, link_path):
    """Создать ярлык через PowerShell."""
    ps = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{link_path}"); '
        f'$s.TargetPath = "{target}"; '
        f'$s.WorkingDirectory = "{os.path.dirname(target)}"; '
        f'$s.Save()'
    )
    subprocess.run(["powershell", "-Command", ps], capture_output=True)


def main():
    # Настраиваем логгер сразу
    log_path = setup_logger()
    if log_path:
        log(f"Лог установки: {log_path}")

    if not _is_admin():
        log("Запуск от имени администратора...")
        run_as_admin()
        return

    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    install_dir = os.path.join(program_files, "AppMonitor")

    log("=" * 50)
    log("  Установка AppMonitor v1.0.0")
    log("=" * 50)

    try:
        # Папка установки
        if not os.path.isdir(install_dir):
            os.makedirs(install_dir)
            log(f"  Создана папка: {install_dir}")

        # Копируем AppMonitor.exe
        base_dir = os.path.dirname(os.path.abspath(__file__))
        src_exe = os.path.join(base_dir, "AppMonitor.exe")

        if not os.path.isfile(src_exe):
            src_exe = os.path.join(sys._MEIPASS, "AppMonitor.exe")
            log(f"  Ищем во временной папке: {src_exe}")

        if not os.path.isfile(src_exe):
            log_error(f"AppMonitor.exe не найден! Искали: {src_exe}")
            input("Нажмите Enter для выхода...")
            return

        dst_exe = os.path.join(install_dir, "AppMonitor.exe")
        shutil.copy2(src_exe, dst_exe)
        log(f"  Скопирован: AppMonitor.exe ({os.path.getsize(dst_exe) / 1024 / 1024:.1f} MB)")

        # Папки для данных и логов
        for d in ["data", "logs"]:
            p = os.path.join(install_dir, d)
            if not os.path.isdir(p):
                os.makedirs(p)
                log(f"  Создана папка: {p}")

        # Ярлык в меню Пуск
        start_menu = os.path.join(
            os.environ.get("ProgramData", "C:\\ProgramData"),
            "Microsoft\\Windows\\Start Menu\\Programs\\AppMonitor"
        )
        if not os.path.isdir(start_menu):
            os.makedirs(start_menu)

        create_shortcut(dst_exe, os.path.join(start_menu, "AppMonitor.lnk"))
        log("  Ярлык в меню Пуск создан")

        # Ярлык на рабочем столе
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        create_shortcut(dst_exe, os.path.join(desktop, "AppMonitor.lnk"))
        log("  Ярлык на рабочем столе создан")

        # Автозагрузка
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "AppMonitor", 0, winreg.REG_SZ, f'"{dst_exe}"')
            winreg.CloseKey(key)
            log("  Добавлено в автозагрузку")
        except Exception as e:
            log_error(f"Ошибка автозагрузки: {e}")

        log("")
        log("=" * 50)
        log("  Установка завершена!")
        log(f"  AppMonitor установлен в: {install_dir}")
        log("=" * 50)
        log("")
        log("  Запуск AppMonitor...")
        subprocess.Popen([dst_exe], cwd=install_dir)

    except Exception as e:
        log_error(f"Критическая ошибка установки: {e}")

    finally:
        if LOG_FILE:
            try:
                LOG_FILE.write(f"Finish: {datetime.datetime.now()}\n")
                LOG_FILE.close()
            except Exception:
                pass

    input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
