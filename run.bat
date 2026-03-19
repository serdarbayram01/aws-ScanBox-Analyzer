@echo off
REM AWS FinOps Dashboard — Windows Launcher

setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo   AWS FinOps Dashboard
echo   ------------------------------------

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
  echo   ERROR: Python not found. Please install Python 3.8+ from python.org
  pause
  exit /b 1
)

REM Create venv if missing
if not exist ".venv\" (
  echo   Creating virtual environment...
  python -m venv .venv
)

REM Activate
call .venv\Scripts\activate.bat

REM Install dependencies
echo   Checking dependencies...
pip install -q -r requirements.txt

echo   Starting server at http://localhost:5100
echo   Press Ctrl+C to stop.
echo.

python app.py
pause
