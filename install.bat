@echo off
chcp 65001 > nul
title Установка LuTools для Python 3.10.5
echo ========================================
echo    Установка LuTools (Python 3.10.5)
echo ========================================
echo.

:: Проверка Python
python --version 2>nul >nul
if errorlevel 1 (
    echo ❌ Python не найден!
    echo Скачайте Python 3.10.5: https://www.python.org/downloads/release/python-3105/
    echo И отметьте "Add Python to PATH"
    pause
    exit /b 1
)

:: Проверка версии Python
python -c "import sys; exit(0) if sys.version_info.major==3 and sys.version_info.minor==10 else exit(1)" 2>nul
if errorlevel 1 (
    echo ❌ Обнаружена неверная версия Python!
    echo Требуется: Python 3.10.5
    echo У вас: 
    python --version
    echo.
    echo Установите Python 3.10.5: https://www.python.org/downloads/release/python-3105/
    pause
    exit /b 1
)

echo ✅ Python 3.10.5 найден
python --version
echo.

echo 1. Обновление pip...
python -m pip install --upgrade pip --quiet
echo ✅ pip обновлен
echo.

echo 2. Установка psutil...
python -m pip install psutil>=5.9.0 --quiet
echo ✅ psutil установлен
echo.

echo 3. Установка mss...
python -m pip install mss>=9.0.1 --quiet
echo ✅ mss установлен
echo.

echo 4. Установка aiogram...
python -m pip install aiogram==2.25.1 --quiet
echo ✅ aiogram установлен
echo.

echo ========================================
echo ✅ ПРОВЕРКА УСТАНОВКИ
echo ========================================
echo.

python -c "
try:
    import aiogram
    import psutil
    import pyautogui
    import mss
    import aiohttp
    
    print('🎉 ВСЕ БИБЛИОТЕКИ УСТАНОВЛЕНЫ!')
    print()
    print('Установленные версии:')
    print(f'• aiogram: {aiogram.__version__}')
    print(f'• aiohttp: {aiohttp.__version__}')
    print(f'• psutil: {psutil.__version__}')
    print(f'• mss: {mss.__version__}')
    print(f'• pyautogui: {pyautogui.__version__}')
    print()
    print('✅ Установка завершена успешно!')
    print('Теперь отредактируйте файл LuTools.py')
    print('и вставьте ваш токен от BotFather')
    
except ImportError as e:
    print(f'❌ Ошибка: {e}')
    print('Не все библиотеки установились.')
    print('Попробуйте установить вручную:')
    print('pip install aiogram==2.25.1 aiohttp==3.8.6 psutil mss pyautogui')
    exit(1)
"

if errorlevel 1 (
    echo.
    pause
    exit /b 1
)

