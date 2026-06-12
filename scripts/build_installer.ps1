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
    $pyprojectPath = "pyproject.toml"
    $content = Get-Content $pyprojectPath -Raw

    if ($content -match 'version = "(\d+)\.(\d+)\.(\d+)"') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        $patch = [int]$Matches[3] + 1
        $newVersion = "$major.$minor.$patch"

        Write-Host "Повышаю версию: $($Matches[0]) -> $newVersion" -ForegroundColor Yellow

        # Обновляем pyproject.toml
        $content = $content -replace 'version = "[\d.]+', "version = `"$newVersion"
        Set-Content $pyprojectPath -Value $content -NoNewline

        # Обновляем core/updater.py (зашитая версия для PyInstaller)
        $updaterPath = "core\updater.py"
        $updaterContent = Get-Content $updaterPath -Raw
        $updaterContent = $updaterContent -replace 'APP_VERSION = "[\d.]+', "APP_VERSION = `"$newVersion"
        Set-Content $updaterPath -Value $updaterContent -NoNewline

        # Обновляем installer/installer.nsi (через Python для CP1251)
        python scripts/patch_nsi.py installer/installer.nsi $newVersion dist\v$newVersion

        Write-Host "[OK] Версия обновлена до $newVersion" -ForegroundColor Green
        return $newVersion
    } else {
        Write-Host "[ОШИБКА] Не удалось найти версию в pyproject.toml" -ForegroundColor Red
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

# Обновляем installer/installer.nsi — OutFile и File в версионную папку
python scripts/patch_nsi.py installer/installer.nsi $newVersion $versionFolder
Write-Host "[INFO] installer.nsi: OutFile и File -> $versionFolder" -ForegroundColor Gray

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

    # PyInstaller всегда кладёт .exe в корень dist/
    $exeTemp = "dist\AppMonitor.exe"
    if (-not (Test-Path $exeTemp)) {
        throw "AppMonitor.exe не найден после сборки PyInstaller"
    }
    # Перемещаем в версионную папку
    Move-Item -Path $exeTemp -Destination "$versionFolder\AppMonitor.exe" -Force
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

    $setupSource = "$versionFolder\AppMonitor_Setup_$newVersion.exe"
    if (-not (Test-Path $setupSource)) {
        throw "Установщик не найден: $setupSource"
    }
    Write-Host "  [OK] Установщик собран" -ForegroundColor Green
}
catch {
    Write-Host "[ОШИБКА] Сборка установщика не удалась: $_" -ForegroundColor Red
    exit 1
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
