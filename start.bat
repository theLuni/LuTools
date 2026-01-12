@echo off
chcp 65001 > nul
title LuTools Bot
echo ========================================
echo          Запуск LuTools Bot
echo ========================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден!
    echo Установите Python 3.7+ и добавьте в PATH
    echo Скачать: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python найден

REM Проверка зависимостей
echo Проверка зависимостей...
python -c "import aiogram, psutil, mss" >nul 2>&1
if errorlevel 1 (
    echo ❌ Не все зависимости установлены
    echo Запустите install_deps.bat для установки
    pause
    exit /b 1
)

echo ✅ Все зависимости установлены
echo.

REM Создание папки для логов если её нет
if not exist "logs" mkdir logs

echo Запуск бота...
echo Для остановки используйте stop.bat
echo Или же можете добавить в автозагрузку autostart.bat
echo ========================================
echo.

REM Запуск бота из папки core
pythonw core\LuTools.py

if errorlevel 1 (
    echo ❌ Ошибка при запуске бота
    pause
    exit /b 1
)