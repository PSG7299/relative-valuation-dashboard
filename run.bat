@echo off
REM ============================================================
REM  Relative Valuation Dashboard - one-click launcher (Windows)
REM ============================================================

cd /d "%~dp0"

echo [1/4] Checking Python...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python not found. Install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [2/4] Setting up virtual environment...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

echo [4/4] Launching Streamlit...
streamlit run app.py

pause
