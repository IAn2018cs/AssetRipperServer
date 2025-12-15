@echo off
REM AssetRipper API Server - Windows Batch Stop Script

echo ========================================
echo   AssetRipper API Server - Stop Service
echo ========================================
echo.

REM Stop uvicorn processes
echo [1/2] Finding and stopping uvicorn processes...
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >NUL
if errorlevel 1 (
    echo Warning: No python processes found
) else (
    echo Stopping uvicorn processes...
    for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID:"') do (
        taskkill /PID %%i /F >NUL 2>&1
    )
    echo OK uvicorn processes stopped
)

REM Stop AssetRipper processes
echo.
echo [2/2] Finding and stopping AssetRipper processes...
tasklist /FI "IMAGENAME eq AssetRipper.GUI.Free.exe" 2>NUL | find /I "AssetRipper.GUI.Free.exe" >NUL
if errorlevel 1 (
    echo Warning: No AssetRipper processes found
) else (
    echo Stopping AssetRipper processes...
    taskkill /IM AssetRipper.GUI.Free.exe /F >NUL 2>&1
    echo OK AssetRipper processes stopped
)

echo.
echo ========================================
echo   Service stop complete!
echo ========================================
echo.
