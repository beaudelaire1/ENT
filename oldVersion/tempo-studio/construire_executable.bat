@echo off
setlocal
cd /d "%~dp0"
echo Installation de l'outil de construction...
python -m pip install --disable-pip-version-check --upgrade pyinstaller
if errorlevel 1 goto :error

echo Construction de Tempo Studio...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --onedir ^
  --name "Tempo Studio" ^
  --add-data "qml;qml" ^
  --add-data "assets;assets" ^
  orateur_timer.py
if errorlevel 1 goto :error

echo.
echo Application creee dans : dist\Tempo Studio
pause
exit /b 0

:error
echo.
echo La construction a echoue. Consultez les messages ci-dessus.
pause
exit /b 1
