@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Run setup_windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install "PyInstaller>=6,<7"
if errorlevel 1 goto failed
rem v0.20 provides built-in QtSvg mascots; the v0.9 ZIP icon may be absent.
rem Do not fail a manual build merely because that old .ico was not recovered.
set "ICON_ARG="
if exist "assets\icons\profmonkey.ico" set "ICON_ARG=--icon assets\icons\profmonkey.ico"
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name ProfMonkeyDesktop %ICON_ARG% --add-data "assets;assets" --add-data "site;site" --add-data "README.md;." app.py
if errorlevel 1 goto failed
echo [OK] dist\ProfMonkeyDesktop\ProfMonkeyDesktop.exe
pause
exit /b 0
:failed
echo [ERROR] Packaging failed.
pause
exit /b 1
