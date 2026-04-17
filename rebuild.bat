@echo off
REM Quick rebuild script for ProMe.exe

echo ====================================
echo  ProMe Rebuild
echo ====================================
echo.
echo Stopping any running ProMe instances...

taskkill /IM ProMe.exe /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1

timeout /t 2 /nobreak

cd /d "%~dp0"

echo.
echo Cleaning old builds...
powershell -Command "Remove-Item -Path dist -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item -Path build -Recurse -Force -ErrorAction SilentlyContinue"

echo.
echo Building ProMe.exe...
pyinstaller ProMe.spec --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo ====================================
    echo [SUCCESS] ProMe.exe built successfully!
    echo ====================================
    echo Location: dist\ProMe.exe
    echo.
) else (
    echo.
    echo [ERROR] Build failed. Check the output above.
    echo.
)

pause
