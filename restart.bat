@echo off
REM AssetRipper API Server - Windows Batch Restart Script

echo ========================================
echo   AssetRipper API Server - Restart
echo ========================================
echo.

REM Stop service
echo Step 1/2: Stopping current service
echo.
call stop.bat

echo.
echo Step 2/2: Starting service
echo.
timeout /t 1 /nobreak >NUL

REM Start service
call start.bat
