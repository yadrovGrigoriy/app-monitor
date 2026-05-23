<#
.SYNOPSIS
    Сборка установщика AppMonitor для Windows.
.DESCRIPTION
    1. Собирает AppMonitor.exe и AppMonitorAdmin.exe через PyInstaller
    2. Собирает установщик через NSIS
    3. Результат: dist\AppMonitor_Setup_<version>.exe
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " AppMonitor — Сборка установщика" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ─── Проверка зависимостей ──────────────────────────────────────────
function Test-Command($cmd) {
    try { Get-Command $cmd -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}

if (-not (Test-Command "pyinstaller")) {
    Write-Host "[ОШИБКА] PyInstaller не найден. Установите: pip install pyinstaller" -ForegroundColor Red
    exit 1
}

if (-not (Test-Command "makensis")) {
    Write-Host "[ОШИБКА] NSIS (makensis) не найден." -ForegroundColor Red
    Write-Host "Установите NSIS: https://nsis.sourceforge.io/Download" -ForegroundColor Yellow
    Write-Host "Или: winget install NSIS.NSIS" -ForegroundColor Yellow
    exit 1
}

# ─── Сборка .exe ─────────────────────────────────────────────────────
try {
    Write-Host "[1/3] Сборка AppMonitor.exe..." -ForegroundColor Yellow
    pyinstaller AppMonitor.spec --noconfirm
    Write-Host "[OK] AppMonitor.exe собран" -ForegroundColor Green

    Write-Host "[2/3] Сборка AppMonitorAdmin.exe..." -ForegroundColor Yellow
    pyinstaller AppMonitorAdmin.spec --noconfirm
    Write-Host "[OK] AppMonitorAdmin.exe собран" -ForegroundColor Green
}
catch {
    Write-Host "[ОШИБКА] Сборка .exe не удалась: $_" -ForegroundColor Red
    exit 1
}

# ─── Сборка установщика ─────────────────────────────────────────────
try {
    Write-Host "[3/3] Сборка установщика (NSIS)..." -ForegroundColor Yellow
    makensis "installer\installer.nsi"
    Write-Host "[OK] Установщик собран" -ForegroundColor Green
}
catch {
    Write-Host "[ОШИБКА] Сборка установщика не удалась: $_" -ForegroundColor Red
    exit 1
}

# ─── Результат ───────────────────────────────────────────────────────
$installer = Get-ChildItem "dist\AppMonitor_Setup_*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ГОТОВО!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
if ($installer) {
    Write-Host "Установщик: $($installer.FullName)" -ForegroundColor White
    Write-Host "Размер: $('{0:N2}' -f ($installer.Length / 1MB)) MB" -ForegroundColor White
}
Write-Host ""
Write-Host "Чтобы установить на другом компьютере:" -ForegroundColor White
Write-Host "  1. Скопируйте установщик на целевой ПК" -ForegroundColor White
Write-Host "  2. Запустите от имени администратора" -ForegroundColor White
Write-Host "  3. Следуйте инструкциям" -ForegroundColor White
Write-Host ""
