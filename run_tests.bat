@echo off
REM ============================================================
REM  Relative Valuation Dashboard - automated test runner
REM ============================================================
cd /d "%~dp0"

if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [1/3] Installing/updating dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt >nul
pip install pytest pytest-cov responses >nul

echo [2/3] Running unit tests (offline, mocked HTTP)...
pytest tests/test_valuation.py tests/test_scraper.py --cov=scraper --cov=valuation --cov-report=term-missing
set OFFLINE_EXIT=%ERRORLEVEL%

echo.
echo [3/3] Running live Screener.in smoke test...
set RUN_LIVE=1
pytest tests/test_live_screener.py -v
set LIVE_EXIT=%ERRORLEVEL%
set RUN_LIVE=

echo.
echo ============================================================
echo  Offline tests exit code: %OFFLINE_EXIT%
echo  Live tests exit code:    %LIVE_EXIT%
echo ============================================================
pause
