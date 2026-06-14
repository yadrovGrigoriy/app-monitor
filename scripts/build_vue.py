"""Сборка Vue-приложения для Admin UI."""
import subprocess
import os
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VUE_DIR = os.path.join(PROJECT_ROOT, "api", "web-vue")
WEB_DIR = os.path.join(PROJECT_ROOT, "api", "web")

os.chdir(VUE_DIR)

print("==================================================")
print("Сборка Vue-приложения...")
print("==================================================")

result = subprocess.run(["npm.cmd", "run", "build"], capture_output=True, text=True)
if result.returncode != 0:
    print("ОШИБКА:")
    print(result.stderr)
    exit(1)

print("OK: Vue-приложение собрано")

# Копируем результат в api/web/
dist_dir = os.path.join(VUE_DIR, "dist")
if os.path.isdir(dist_dir):
    if os.path.isdir(WEB_DIR):
        shutil.rmtree(WEB_DIR)
    shutil.copytree(dist_dir, WEB_DIR)
    print(f"OK: Результат скопирован в {WEB_DIR}")
else:
    print(f"ПРЕДУПРЕЖДЕНИЕ: папка dist не найдена в {VUE_DIR}")

print("Готово!")
