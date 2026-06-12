@echo off
chcp 65001 >nul
title AppMonitor — Сборка установщика
echo ============================================
echo  AppMonitor — Сборка установщика
echo ============================================
echo.

:: ─── Проверка Python ───────────────────────────────────────────────
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Python не найден. Установите Python 3.12+
    pause
    exit /b 1
)

:: ─── Проверка PyInstaller ──────────────────────────────────────────
where pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] PyInstaller не найден. Установите: pip install pyinstaller
    pause
    exit /b 1
)

:: ─── Проверка makensis (NSIS) ──────────────────────────────────────
where makensis >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] NSIS (makensis) не найден.
    echo Установите NSIS: https://nsis.sourceforge.io/Download
    echo Или вручную: winget install NSIS.NSIS
    pause
    exit /b 1
)

:: ─── Переход в корень проекта ──────────────────────────────────────
cd /d "%~dp0.."

:: ─── Сборка Vue.js веб-интерфейса ──────────────────────────────────
echo [1/3] Сборка Vue.js веб-интерфейса...
cd api\web-vue
call npm run build
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Сборка Vue.js не удалась
    pause
    exit /b 1
)
cd ..\..
:: Копируем результат в api/web/
if exist "api\web" rmdir /s /q "api\web"
xcopy /e /i /q "api\web-vue\dist" "api\web"
echo [OK] Vue.js веб-интерфейс собран

:: ─── Сборка AppMonitor.exe ─────────────────────────────────────────
echo [2/3] Сборка AppMonitor.exe...
pyinstaller AppMonitor.spec --noconfirm
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Сборка AppMonitor.exe не удалась
    pause
    exit /b 1
)
echo [OK] AppMonitor.exe собран

:: ─── Сборка установщика ────────────────────────────────────────────
echo [3/3] Сборка установщика (NSIS)...
makensis installer\installer.nsi
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Сборка установщика не удалась
    pause
    exit /b 1
)

echo.
echo ============================================
echo  ГОТОВО!
echo ============================================
echo.
echo Установщик: dist\AppMonitor_Setup_*.exe
echo.
echo Чтобы установить на другом компьютере:
echo   1. Скопируйте установщик на целевой ПК
echo   2. Запустите от имени администратора
echo   3. Следуйте инструкциям
echo.
pause
