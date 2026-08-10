@echo off
setlocal
cd /d "%~dp0"
python -c "import PySide6" 2>nul
if errorlevel 1 (
    echo Installation de l'interface moderne PySide6...
    python -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo.
        echo L'installation a echoue. Verifiez que Python et Internet sont disponibles.
        pause
        exit /b 1
    )
)
python orateur_timer.py
if errorlevel 1 pause
