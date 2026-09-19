@echo off
chcp 65001 >nul
title Steam Clone Launcher
cd /d "%~dp0"

echo ============================================
echo    STEAM CLONE LAUNCHER
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден. Установите его с https://python.org
    pause
    exit /b 1
)

python -c "import PyQt6.QtWebEngineWidgets" >nul 2>&1
if errorlevel 1 (
    echo [i] Устанавливаю зависимости лаунчера...
    pip install -r requirements-launcher.txt
    echo.
)

echo [✓] Запускаю лаунчер...
python launcher_api\launcher.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось запустить лаунчер.
    echo Попробуйте вручную:
    echo   pip install -r requirements-launcher.txt
    echo   python launcher_api\launcher.py
    pause
)