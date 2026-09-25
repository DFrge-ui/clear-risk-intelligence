@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run run_windows.bat once to prepare Python, then close its server.
    pause
    popd
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto failed
pause
popd
exit /b 0
:failed
echo Check the error above.
pause
popd
exit /b 1
