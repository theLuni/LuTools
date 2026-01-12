@echo off
chcp 65001 > nul
title LuTools Bot

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден!
    exit /b 1
)

REM Проверка зависимостей
python -c "import aiogram, psutil, mss" >nul 2>&1
if errorlevel 1 (
    echo ❌ Не все зависимости установлены
    exit /b 1
)

REM Создание папки для логов если её нет
if not exist "logs" mkdir logs

REM Запуск бота из папки core
start "LuTools Bot" /B pythonw core\LuTools.py

exit /b 0