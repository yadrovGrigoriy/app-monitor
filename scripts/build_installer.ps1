<#
.SYNOPSIS
    Сборка установщика AppMonitor для Windows.
.DESCRIPTION
    1. Собирает Vue.js веб-интерфейс (npm run build)
    2. Собирает AppMonitor.exe через PyInstaller
    3. Собирает установщик через NSIS
    4. Результат: dist\AppMonitor_Setup_<version>.exe
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

# ─── Сборка Vue.js веб-интерфейса ────────────────────────────────────
try {
    Write-Host "[1/3] Сборка Vue.js веб-интерфейса..." -ForegroundColor Yellow
    Set-Location "api\web-vue"
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm build failed" }
    Set-Location $ProjectRoot
    # Копируем результат в api/web/
    $webDist = "api\web-vue\dist"
    $webTarget = "api\web"
    Remove-Item -Path $webTarget -Recurse -Force -ErrorAction SilentlyContinue
    Copy-Item -Path $webDist -Destination $webTarget -Recurse
    Write-Host "[OK] Vue.js веб-интерфейс собран" -ForegroundColor Green
}
catch {
    Write-Host "[ОШИБКА] Сборка Vue.js не удалась: $_" -ForegroundColor Red
    Set-Location $ProjectRoot
    exit 1
}

# ─── Сборка .exe ─────────────────────────────────────────────────────
try {
    Write-Host "[2/3] Сборка AppMonitor.exe..." -ForegroundColor Yellow
    Write-Host "  -> Запуск PyInstaller (это может занять 2-5 минут)..." -ForegroundColor Gray
    $pyiResult = pyinstaller AppMonitor.spec --noconfirm 2>&1
    Write-Host $pyiResult -ForegroundColor Gray

    # PyInstaller кладёт .exe в dist/ (без подпапки)
    $exeSource = "dist\AppMonitor.exe"
    if (-not (Test-Path $exeSource)) {
        throw "AppMonitor.exe не найден после сборки PyInstaller"
    }
    $exeSize = (Get-Item $exeSource).Length
    Write-Host "  [OK] AppMonitor.exe собран ($('{0:N2}' -f ($exeSize / 1MB)) MB)" -ForegroundColor Green
}
catch {
    Write-Host "[ОШИБКА] Сборка .exe не удалась: $_" -ForegroundColor Red
    exit 1
}

# ─── Сборка установщика ─────────────────────────────────────────────
try {
    Write-Host "[3/3] Сборка установщика (NSIS)..." -ForegroundColor Yellow

    & $makensisPath "installer\installer.nsi" 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

    $setupSource = "dist\AppMonitor_Setup_$newVersion.exe"
    if (-not (Test-Path $setupSource)) {
        throw "Установщик не найден: $setupSource"
    }
    Write-Host "  [OK] Установщик собран" -ForegroundColor Green
}
catch {
    Write-Host "[ОШИБКА] Сборка установщика не удалась: $_" -ForegroundColor Red
    exit 1
}

# ─── Перемещение в версионную папку ─────────────────────────────────
Write-Host ""
Write-Host "Перемещение в папку $versionFolder..." -ForegroundColor Yellow
Move-Item -Path $exeSource -Destination "$versionFolder\AppMonitor.exe" -Force
Move-Item -Path $setupSource -Destination "$versionFolder\AppMonitor_Setup_$newVersion.exe" -Force
Write-Host "[OK] Файлы перемещены" -ForegroundColor Green

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
