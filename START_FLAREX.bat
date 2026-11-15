@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer is required. Install from https://www.python.org/downloads/
  echo Enable Add Python to PATH during installation.
  pause
  exit /b 1
)
if not exist "backend\app\main.py" (
  echo Backend files missing. Extract the complete ZIP first.
  pause
  exit /b 1
)
if not exist "frontend\flame.html" (
  echo frontend\flame.html is missing.
  pause
  exit /b 1
)
start "FLARE-X Backend" cmd /k "cd /d "%~dp0backend" && if not exist .venv py -m venv .venv && call .venv\Scripts\activate.bat && python -m pip install -r requirements.txt && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "FLARE-X Frontend" cmd /k "cd /d "%~dp0frontend" && py -m http.server 5500 --bind 127.0.0.1"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5500/flame.html"
echo Keep both server windows open while using FLARE-X.
pause
