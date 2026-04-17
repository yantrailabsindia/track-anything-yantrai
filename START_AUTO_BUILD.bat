@echo off
REM This script starts the automatic build watcher
REM The watcher will monitor Python files and rebuild ProMe.exe automatically

cd /d "%~dp0"

echo.
echo ===============================================
echo   ProMe Agent - Auto-Build Watcher
echo ===============================================
echo.
echo Checking dependencies...
echo.

REM Check if watchdog is installed
python -m pip show watchdog >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing watchdog...
    python -m pip install watchdog -q
)

REM Check if pyinstaller is installed
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing pyinstaller...
    python -m pip install pyinstaller -q
)

echo.
echo ===============================================
echo   WATCHER STARTED
echo ===============================================
echo.
echo Watching for changes in:
echo   - desktop\*.py
echo   - desktop\ui\*.py
echo   - desktop\trackers\*.py
echo.
echo Auto-rebuild will trigger 2 seconds after you save a file.
echo.
echo To STOP the watcher: Press Ctrl+C
echo.
echo ===============================================
echo.

python build_watcher.py

pause
