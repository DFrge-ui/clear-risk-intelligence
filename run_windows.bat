@echo off
setlocal
pushd "%~dp0"
echo.
echo   CLEAR - Risk Intelligence
echo   AI-assisted learning project - synthetic data only
echo.
if exist ".venv\Scripts\python.exe" goto check_runtime
echo Preparing the local Python environment...
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv .venv
    goto check_venv
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 (
    python -m venv .venv
    goto check_venv
)
echo Python 3.11 or newer was not found.
echo Install Python from https://www.python.org/downloads/windows/
echo Enable "Add Python to PATH", then run this file again.
goto failed
:check_venv
if not exist ".venv\Scripts\python.exe" goto failed
:check_runtime
".venv\Scripts\python.exe" -c "import flask, waitress" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies. Internet is needed for this first setup only.
    ".venv\Scripts\python.exe" -m pip install -r requirements.lock
    if errorlevel 1 goto failed
)
echo Opening http://127.0.0.1:5000 in your browser.
echo Keep this window open. Press Ctrl+C to stop the server.
".venv\Scripts\python.exe" app.py --open %*
if errorlevel 1 goto failed
popd
exit /b 0
:failed
echo.
echo The app could not start. Check the error above and README_RU.md.
echo If port 5000 is busy, run: run_windows.bat --port 5055
pause
popd
exit /b 1
