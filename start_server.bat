@echo off
chcp 65001 >nul
echo === Подготовка сервера к запуску ===

:: Заходим в папку, где лежит этот .bat файл
cd /d "%~dp0"

:: 1. Создаем виртуальное окружение, если его нет
if not exist ".venv\Scripts\python.exe" (
    echo Создаю виртуальное окружение...
    py -3.14 -m venv .venv
)

:: 2. Обновляем установщик pip
echo Обновляю PIP...
.venv\Scripts\python.exe -m pip install --upgrade pip

:: 3. Устанавливаем библиотеки (теперь только websockets)
echo Устанавливаю библиотеки...
.venv\Scripts\python.exe -m pip install -r requirements.txt

:: 4. Запускаем сервер
echo.
echo Запускаю сервер...
echo ====================================
.venv\Scripts\python.exe TestServerPython.py

pause