@echo off
REM ProMe Auto-Build Watcher
REM Monitors Python files and rebuilds ProMe.exe when changes are detected

cd /d "%~dp0"

echo ====================================
echo  ProMe Auto-Build Watcher
echo ====================================
echo.

REM Check if watchdog is installed
python -m pip show watchdog >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing watchdog (file monitor)...
    python -m pip install watchdog -q
)

REM Check if pyinstaller is installed
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing pyinstaller...
    python -m pip install pyinstaller -q
)

echo.
echo Watching for changes in:
echo  - desktop\*.py
echo  - desktop\ui\*.py
echo  - desktop\trackers\*.py
echo.
echo PyInstaller will rebuild automatically when files change.
echo Press Ctrl+C to stop.
echo.

REM Run the watcher (build_watcher.py is now a standalone file)
python build_watcher.py

pause
