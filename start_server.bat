@echo off
chcp 65001 >nul
echo === Подготовка сервера к запуску ===

:: 1. Проверяем, есть ли уже виртуальное окружение
if not exist ".venv" (
    echo Создаю виртуальное окружение...
    python -m venv .venv
)

:: 2. Активируем виртуальное окружение
echo Активирую окружение...
call .venv\Scripts\activate.bat

:: 3. Устанавливаем/обновляем зависимости
echo Устанавливаю библиотеки...
pip install -r requirements.txt

:: 4. Запускаем сервер
echo Запускаю сервер...
echo.
python TestServerPython.py

pause