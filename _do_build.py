"""
Сборка AppMonitor: копирует проект в путь без кириллицы и запускает PyInstaller.
"""
import os
import sys
import shutil
import subprocess
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Целевая директория без кириллицы
BUILD_ROOT = r'C:\Users\Public\AppMonitorBuild'

def main():
    print('=== Копирование проекта в путь без кириллицы ===')
    print(f'Исходник: {PROJECT_ROOT}')
    print(f'Цель: {BUILD_ROOT}')

    # Удаляем старую копию
    if os.path.isdir(BUILD_ROOT):
        shutil.rmtree(BUILD_ROOT)
        print('Старая копия удалена')

    # Копируем (исключая .venv, .git, __pycache__)
    def ignore_func(src, names):
        ignored = set()
        for name in names:
            # Игнорируем зарезервированные имена Windows
            if name.lower() in ('nul', 'con', 'prn', 'aux', 'com1', 'com2', 'lpt1', 'lpt2'):
                ignored.add(name)
                continue
            full = os.path.join(src, name)
            if os.path.isdir(full):
                if name in ('.venv', '.git', '__pycache__', '.idea', '.pytest_cache', '.veai', 'build', 'dist'):
                    ignored.add(name)
        return ignored

    shutil.copytree(PROJECT_ROOT, BUILD_ROOT, ignore=ignore_func)
    print('Проект скопирован')

    # Создаём виртуальное окружение в целевой директории
    venv_dir = os.path.join(BUILD_ROOT, '.venv')
    if not os.path.isdir(venv_dir):
        print('Создание виртуального окружения...')
        subprocess.run([sys.executable, '-m', 'venv', venv_dir], check=True)
        print('Виртуальное окружение создано')

    # Определяем python из venv
    python_exe = os.path.join(venv_dir, 'Scripts', 'python.exe')

    # Устанавливаем зависимости
    print('Установка зависимостей...')
    req_file = os.path.join(BUILD_ROOT, 'requirements.txt')
    subprocess.run([python_exe, '-m', 'pip', 'install', '-r', req_file], check=True)
    subprocess.run([python_exe, '-m', 'pip', 'install', 'pyinstaller', 'pillow'], check=True)
    print('Зависимости установлены')

    # Генерируем иконку (без PyQt5, только PIL)
    print('Генерация иконки...')
    gen_icon = os.path.join(BUILD_ROOT, '_gen_icon_simple.py')
    if os.path.isfile(gen_icon):
        subprocess.run([python_exe, gen_icon], cwd=BUILD_ROOT, check=True)
        print('Иконка сгенерирована')

    # Запускаем PyInstaller через spec
    print('Запуск PyInstaller...')
    spec_file = os.path.join(BUILD_ROOT, 'appmonitor.spec')
    dist_dir = os.path.join(BUILD_ROOT, 'dist')
    work_dir = os.path.join(BUILD_ROOT, 'build')

    cmd = [
        python_exe, '-m', 'PyInstaller',
        spec_file,
        '--noconfirm',
        '--clean',
        '--distpath', dist_dir,
        '--workpath', work_dir,
    ]
    result = subprocess.run(cmd, cwd=BUILD_ROOT)
    if result.returncode != 0:
        print(f'ОШИБКА: PyInstaller завершился с кодом {result.returncode}')
        sys.exit(1)

    # Копируем результат обратно
    exe_src = os.path.join(dist_dir, 'AppMonitor.exe')
    exe_dst = os.path.join(PROJECT_ROOT, 'dist', 'AppMonitor.exe')
    os.makedirs(os.path.dirname(exe_dst), exist_ok=True)
    shutil.copy2(exe_src, exe_dst)
    print(f'✅ EXE скопирован: {exe_dst}')

    size_mb = os.path.getsize(exe_dst) / (1024 * 1024)
    print(f'   Размер: {size_mb:.1f} MB')


if __name__ == '__main__':
    main()
