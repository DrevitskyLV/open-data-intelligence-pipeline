@echo off
setlocal
cd /d "%~dp0"

echo.
echo =====================================================
echo   Open Data Intelligence Pipeline - local demo
echo =====================================================
echo.

py -3.12 --version >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_COMMAND=py -3.12"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python was not found.
        echo Install Python 3.12 from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    python -c "import sys; raise SystemExit(0 if sys.version_info ^>= (3, 12) else 1)"
    if errorlevel 1 (
        echo Python 3.12 or newer is required.
        echo Install it from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set "PYTHON_COMMAND=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    %PYTHON_COMMAND% -m venv .venv
    if errorlevel 1 goto :failure
) else (
    echo [1/3] Virtual environment already exists.
)

if not exist ".venv\Scripts\uvicorn.exe" (
    echo [2/3] Installing dependencies. This is required only once...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :failure
    ".venv\Scripts\python.exe" -m pip install -e "."
    if errorlevel 1 goto :failure
) else (
    echo [2/3] Dependencies are already installed.
)

echo [3/3] Starting demo at http://127.0.0.1:8000/dashboard
echo.
echo Keep this window open while testing the demo.
echo Press Ctrl+C here to stop the server.
echo.

start "" powershell -NoProfile -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000/dashboard'"
".venv\Scripts\uvicorn.exe" open_data_intelligence.main:app --host 127.0.0.1 --port 8000
exit /b 0

:failure
echo.
echo Demo setup failed. Copy the error above and send it to me.
pause
exit /b 1
