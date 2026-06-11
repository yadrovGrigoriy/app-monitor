<#
.SYNOPSIS
    Сборка установщика AppMonitor для Windows.
.DESCRIPTION
    1. Собирает AppMonitor.exe и AppMonitorAdmin.exe через PyInstaller
    2. Собирает установщик через NSIS
    3. Результат: dist\AppMonitor_Setup_<version>.exe
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Location).Path
Set-Location $ProjectRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " AppMonitor — Сборка установщика" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ─── Автоинкремент версии ────────────────────────────────────────────
function Update-Version {
    $updaterPath = "core\updater.py"
    $content = Get-Content $updaterPath -Raw

    if ($content -match 'APP_VERSION = "(\d+)\.(\d+)\.(\d+)"') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        $patch = [int]$Matches[3] + 1
        $newVersion = "$major.$minor.$patch"

        Write-Host "Повышаю версию: $($Matches[0]) -> $newVersion" -ForegroundColor Yellow

        # Обновляем core/updater.py
        $content = $content -replace 'APP_VERSION = "[\d.]+"', "APP_VERSION = `"$newVersion`""
        Set-Content $updaterPath -Value $content -NoNewline

        # Обновляем api/admin_server.py
        $adminPath = "api\admin_server.py"
        $adminContent = Get-Content $adminPath -Raw
        $adminContent = $adminContent -replace 'APP_VERSION = "[\d.]+"', "APP_VERSION = `"$newVersion`""
        Set-Content $adminPath -Value $adminContent -NoNewline

        # Обновляем installer/installer.nsi
        $nsiPath = "installer\installer.nsi"
        $nsiContent = Get-Content $nsiPath -Raw
        $nsiContent = $nsiContent -replace '!define PRODUCT_VERSION "[\d.]+"', "!define PRODUCT_VERSION `"$newVersion`""
        Set-Content $nsiPath -Value $nsiContent -NoNewline

        Write-Host "[OK] Версия обновлена до $newVersion" -ForegroundColor Green
        return $newVersion
    } else {
        Write-Host "[ОШИБКА] Не удалось найти версию в core\updater.py" -ForegroundColor Red
        exit 1
    }
}

$newVersion = Update-Version

# ─── Проверка зависимостей ──────────────────────────────────────────
function Test-Command($cmd) {
    try { Get-Command $cmd -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}

if (-not (Test-Command "pyinstaller")) {
    Write-Host "[ОШИБКА] PyInstaller не найден. Установите: pip install pyinstaller" -ForegroundColor Red
    exit 1
}

if (-not (Test-Command "makensis") -and -not (Test-Path "C:\Program Files (x86)\NSIS\makensis.exe")) {
    Write-Host "[ОШИБКА] NSIS (makensis) не найден." -ForegroundColor Red
    Write-Host "Установите NSIS: https://nsis.sourceforge.io/Download" -ForegroundColor Yellow
    Write-Host "Или: winget install NSIS.NSIS" -ForegroundColor Yellow
    exit 1
}

# Определяем путь к makensis
$makensisPath = if (Test-Command "makensis") { "makensis" } else { "C:\Program Files (x86)\NSIS\makensis.exe" }

# ─── Папка для сборки ───────────────────────────────────────────────
$versionFolder = "dist\v$newVersion"
$tempFolder = "dist\.temp_build"
New-Item -ItemType Directory -Path $versionFolder -Force | Out-Null
Remove-Item -Path $tempFolder -Recurse -Force -ErrorAction SilentlyContinue

# ─── Сборка .exe ─────────────────────────────────────────────────────
try {
    Write-Host "[1/3] Сборка AppMonitor.exe..." -ForegroundColor Yellow
    pyinstaller AppMonitor.spec --noconfirm --distpath $tempFolder
    # PyInstaller создаёт подпапку с именем spec-файла, перемещаем .exe
    Get-ChildItem "$tempFolder\AppMonitor\AppMonitor.exe" -ErrorAction SilentlyContinue | Move-Item -Destination "$versionFolder\AppMonitor.exe" -Force
    Get-ChildItem "$tempFolder\AppMonitor.exe" -ErrorAction SilentlyContinue | Move-Item -Destination "$versionFolder\AppMonitor.exe" -Force
    Write-Host "[OK] AppMonitor.exe собран" -ForegroundColor Green

    Write-Host "[2/3] Сборка AppMonitorAdmin.exe..." -ForegroundColor Yellow
    pyinstaller AppMonitorAdmin.spec --noconfirm --distpath $tempFolder
    Get-ChildItem "$tempFolder\AppMonitorAdmin\AppMonitorAdmin.exe" -ErrorAction SilentlyContinue | Move-Item -Destination "$versionFolder\AppMonitorAdmin.exe" -Force
    Get-ChildItem "$tempFolder\AppMonitorAdmin.exe" -ErrorAction SilentlyContinue | Move-Item -Destination "$versionFolder\AppMonitorAdmin.exe" -Force
    Write-Host "[OK] AppMonitorAdmin.exe собран" -ForegroundColor Green
}
catch {
    Write-Host "[ОШИБКА] Сборка .exe не удалась: $_" -ForegroundColor Red
    exit 1
}
finally {
    Remove-Item -Path $tempFolder -Recurse -Force -ErrorAction SilentlyContinue
}

# ─── Сборка установщика ─────────────────────────────────────────────
try {
    Write-Host "[3/3] Сборка установщика (NSIS)..." -ForegroundColor Yellow

    # Создаём временную копию installer.nsi с путями к папке версии
    $nsiContent = Get-Content "installer\installer.nsi" -Raw
    $nsiContent = $nsiContent -replace 'File "\.\.\\dist\\AppMonitor\.exe"', "File `"..\$versionFolder\AppMonitor.exe`""
    $nsiContent = $nsiContent -replace 'File "\.\.\\dist\\AppMonitorAdmin\.exe"', "File `"..\$versionFolder\AppMonitorAdmin.exe`""
    $nsiContent = $nsiContent -replace 'OutFile "\.\.\\dist\\AppMonitor_Setup_', "OutFile `"..\$versionFolder\AppMonitor_Setup_"
    $tempNsi = "installer\.temp_build.nsi"
    Set-Content $tempNsi -Value $nsiContent -NoNewline

    & $makensisPath $tempNsi
    Remove-Item $tempNsi -Force -ErrorAction SilentlyContinue

    Write-Host "[OK] Установщик собран" -ForegroundColor Green
}
catch {
    Write-Host "[ОШИБКА] Сборка установщика не удалась: $_" -ForegroundColor Red
    exit 1
}

# ─── Очистка БД ────────────────────────────────────────────────────
try {
    Write-Host "[4/4] Очистка пользовательских данных в БД..." -ForegroundColor Yellow
    python -c "
import sys
sys.path.insert(0, '.')
from core.database import Database
db = Database()
db.clear_data()
print('OK')
"
    Write-Host "[OK] Данные в БД очищены" -ForegroundColor Green
}
catch {
    Write-Host "[ПРЕДУПРЕЖДЕНИЕ] Не удалось очистить БД: $_" -ForegroundColor Yellow
}

# ─── Результат ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ГОТОВО!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Папка сборки: $versionFolder" -ForegroundColor White
Write-Host ""
$items = Get-ChildItem $versionFolder
foreach ($item in $items) {
    Write-Host "  - $($item.Name)  ($('{0:N2}' -f ($item.Length / 1MB)) MB)" -ForegroundColor White
}
Write-Host ""
Write-Host "Чтобы установить на другом компьютере:" -ForegroundColor White
Write-Host "  1. Скопируйте папку v$newVersion на целевой ПК" -ForegroundColor White
Write-Host "  2. Запустите AppMonitor_Setup_$newVersion.exe от имени администратора" -ForegroundColor White
Write-Host "  3. Следуйте инструкциям" -ForegroundColor White
Write-Host ""
