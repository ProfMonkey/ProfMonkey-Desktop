@echo off
setlocal
cd /d "%~dp0"
echo [ProfMonkey] Creating Python virtual environment...
py -3.12 -m venv .venv
if errorlevel 1 (
  echo Python 3.12 unavailable, falling back to installed Python 3.
  py -3 -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Please install Python 3.12 from python.org, then retry.
    pause
    exit /b 1
  )
)
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo [OK] Setup done. Double-click run_windows.bat.
pause
exit /b 0
:failed
echo [ERROR] Package installation failed. Check network access and Python.
pause
exit /b 1
