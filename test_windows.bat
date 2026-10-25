@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 goto fail
echo [OK] Python and Qt import tests completed. Manual Windows UI checks are still required.
pause
exit /b 0
:fail
echo [FAILED] Review the output above.
pause
exit /b 1
