"""Скрипт для коммита изменений в git."""
import subprocess
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

# 1. Статус
print("=" * 50)
print("git status")
print("=" * 50)
subprocess.run(["git", "status"], check=False)

# 2. Добавляем все изменения
print("\n" + "=" * 50)
print("git add .")
print("=" * 50)
subprocess.run(["git", "add", "."], check=False)

# 3. Коммит
print("\n" + "=" * 50)
print("git commit")
print("=" * 50)
result = subprocess.run(
    ["git", "commit", "-m", "feat: add logs viewer to webui, fix updater and version detection"],
    check=False,
)
if result.returncode == 0:
    print("\nOK: Коммит создан")
else:
    print("\nОшибка коммита (возможно, нечего коммитить)")
