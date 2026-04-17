@echo off
echo Starting ProMe Agent (Debug Mode)...
echo.
cd /d "%~dp0"
REM Run the ProMe exe and keep console open
dist\ProMe.exe
pause
