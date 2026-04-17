@echo off
REM This script starts the automatic build watcher
REM The watcher will monitor Python files and rebuild executables automatically

cd /d "%~dp0"

echo.
echo ===============================================
echo   Windows Agent and CCTV Agent - Auto-Build Watcher
echo ===============================================
echo.

REM Clear old log file
if exist build_watcher.log del build_watcher.log

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
echo   WATCHER STARTING...
echo ===============================================
echo.
echo Logs will be written to: build_watcher.log
echo.
echo Auto-rebuild will trigger 2 seconds after you save a file.
echo Build time is usually 2-3 minutes.
echo.
echo To STOP the watcher: Press Ctrl+C
echo.
echo ===============================================
echo.

python build_watcher.py

pause
