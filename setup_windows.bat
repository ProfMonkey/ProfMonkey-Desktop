@echo off
setlocal
cd /d "%~dp0"
echo [ProfMonkey] Checking Python environment...
if not exist ".venv\Scripts\python.exe" (
  echo [ProfMonkey] Creating Python virtual environment...
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo Python 3.12 unavailable, falling back to installed Python 3.
    py -3 -m venv .venv
    if errorlevel 1 (
      echo [ERROR] Please install Python 3.12 or newer from python.org, then retry.
      pause
      exit /b 1
    )
  )
)
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo [ProfMonkey] Verifying Pillow and QtSvg...
.venv\Scripts\python.exe -c "from PIL import Image; from PySide6.QtSvg import QSvgRenderer; print('Pillow', Image.__version__, '| QtSvg OK')" >nul 2>&1
if errorlevel 1 (
  echo [Repair] Pillow appears damaged. Reinstalling its binary wheel...
  .venv\Scripts\python.exe -m pip install --no-cache-dir --force-reinstall "Pillow>=10,<13"
  if errorlevel 1 goto failed
)
.venv\Scripts\python.exe -c "from PIL import Image; import PySide6; from PySide6.QtSvg import QSvgRenderer; print('Pillow', Image.__version__, '| PySide6', PySide6.__version__, '| QtSvg OK)"
if errorlevel 1 goto failed
echo [OK] Setup and import checks passed. Double-click run_windows.bat.
pause
exit /b 0
:failed
echo [ERROR] Setup/import verification failed.
echo Try deleting only the .venv folder and run setup_windows.bat again.
pause
exit /b 1
