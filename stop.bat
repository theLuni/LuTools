@echo off
chcp 65001 > nul
title Остановка LuTools
echo ========================================
echo          Остановка LuTools
echo ========================================
echo.

echo 🔍 Поиск запущенных процессов LuTools...

REM Поиск и завершение процессов Python с LuTools
for /f "tokens=2" %%a in ('tasklist ^| findstr /i "python.*LuTools"') do (
    echo Завершение процесса PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

REM Альтернативный поиск по имени файла
for /f "tokens=2" %%a in ('tasklist ^| findstr /i "pythonw.exe"') do (
    echo Завершение фонового процесса PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

REM Удаление временных файлов если есть
if exist "__pycache__" (
    echo Очистка кеша...
    rmdir /s /q "__pycache__"
)

if exist "*.pyc" (
    del /q "*.pyc"
)

echo.
echo ✅ LuTools остановлен
echo Все процессы завершены
echo.
pause