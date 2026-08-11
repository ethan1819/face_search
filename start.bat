@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONPATH="
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Project virtual environment was not found.
  echo Run the installation command from README.md first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m app.main
if errorlevel 1 (
  echo.
  echo ERROR: The application exited with an error.
  echo Check data\logs\app.log for details.
  pause
  exit /b 1
)
endlocal
