@echo off
setlocal

:: Get the directory of the script
set "project_root=%~dp0"
cd /d "%project_root%"

:: Absolute path to Python (Detected)
set "PYW=C:\Users\WELCOME\AppData\Local\Programs\Python\Python312\pythonw.exe"

echo Starting CCTV Agent in Silent Mode...

:: Start the Tray Monitor (PySide6)
start "" "%PYW%" -m cctv_agent.ui.tray_app

:: Wait 2 seconds for UI to initialize
timeout /t 2 /nobreak > nul

:: Start the Main Capture & Tunnel Service
start "" "%PYW%" -m cctv_agent.main_service

echo Agent is running in the system tray.
exit
