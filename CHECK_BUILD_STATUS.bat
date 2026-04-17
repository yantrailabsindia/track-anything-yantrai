@echo off
REM Check Build Status Helper
REM Shows the status of the auto-build watcher and latest builds

cd /d "%~dp0"

echo.
echo ===============================================
echo   AUTO-BUILD STATUS CHECK
echo ===============================================
echo.

REM 1. Check if watcher is running
tasklist /FI "IMAGENAME eq python.exe" /V | findstr /I "build_watcher.py" >nul
if %errorlevel% equ 0 (
    echo [STATUS] Watcher is ACTIVE
) else (
    echo [STATUS] Watcher is NOT RUNNING
    echo          Run START_AUTO_BUILD.bat to start it.
)

echo.
echo [LATEST BUILDS]
echo -----------------------------------------------
powershell -Command "Get-ChildItem -Path dist\WindowsAgent.exe, dist\CCTVAgent.exe -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime, @{Name='Size(MB)';Expression={'{0:N2}' -f ($_.Length / 1MB)}} | Format-Table -AutoSize"

echo.
echo [LATEST LOG ENTRIES] (from build_watcher.log)
echo -----------------------------------------------
if exist build_watcher.log (
    powershell -Command "Get-Content build_watcher.log | Select-Object -Last 10"
) else (
    echo No log file found.
)

echo.
echo ===============================================
pause
