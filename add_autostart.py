import os, json
base = "C:/Users/Григорий/code/AppMonitor"
json_path = os.path.join(base, "project_files.json")
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

data["core/autostart.py"] = """import os
import sys


class AutostartManager:
    REGISTRY_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
    APP_NAME = 'AppMonitor'

    def __init__(self):
        self.app_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])

    def enable(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, self.APP_NAME, 0, winreg.REG_SZ, f'"{self.app_path}"')
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def disable(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, self.APP_NAME)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def is_autostart_enabled(self) -> bool:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, self.APP_NAME)
            winreg.CloseKey(key)
            return value == f'"{self.app_path}"'
        except (FileNotFoundError, OSError):
            return False
        except Exception:
            return False
"""

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)
print("OK")
