@echo off
REM AssetRipper API Server - Windows Batch Startup Script
REM Simple batch file alternative to PowerShell script

setlocal enabledelayedexpansion

echo ========================================
echo   AssetRipper API Server - Startup
echo ========================================
echo.

REM Check Python
echo [1/7] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3.11+ not found. Please install Python first.
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo OK Python version: %PYTHON_VERSION%

REM Check if in project root
if not exist "requirements.txt" (
    echo Error: Please run this script from the project root directory
    exit /b 1
)

REM Setup virtual environment
echo.
echo [2/7] Setting up Python virtual environment...
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    echo OK Virtual environment created
) else (
    echo OK Virtual environment already exists
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies
echo.
echo [3/7] Installing Python dependencies...
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo OK Dependencies installed

REM Check AssetRipper binary
echo.
echo [4/7] Checking AssetRipper binary...
set ASSETRIPPER_PATH=
if exist "local\AssetRipper.GUI.Free.exe" (
    set ASSETRIPPER_PATH=%CD%\local\AssetRipper.GUI.Free.exe
    echo OK Found Windows version: local\AssetRipper.GUI.Free.exe
) else if exist "bin\AssetRipper.GUI.Free.exe" (
    set ASSETRIPPER_PATH=%CD%\bin\AssetRipper.GUI.Free.exe
    echo OK Found Windows version: bin\AssetRipper.GUI.Free.exe
) else (
    echo Error: AssetRipper.GUI.Free.exe not found
    echo.
    echo Please place the Windows version of AssetRipper.GUI.Free.exe in:
    echo   1. local\AssetRipper.GUI.Free.exe (recommended)
    echo   2. bin\AssetRipper.GUI.Free.exe
    echo.
    echo Download: https://github.com/AssetRipper/AssetRipper/releases
    exit /b 1
)

REM Create directories
echo.
echo [5/7] Creating data directories...
if not exist "data\uploads" mkdir data\uploads
if not exist "data\exports" mkdir data\exports
if not exist "data\db" mkdir data\db
if not exist "logs" mkdir logs
echo OK Directories created

REM Set environment variables
echo.
echo [6/7] Configuring environment variables...
set ENVIRONMENT=development
set API_HOST=0.0.0.0
set API_PORT=8000
set ASSETRIPPER_PORT=8765
set ASSETRIPPER_BINARY_PATH=%ASSETRIPPER_PATH%
set DATABASE_URL=sqlite+aiosqlite:///%CD%/data/db/assetripper.db
set DATABASE_URL=%DATABASE_URL:\=/%
set UPLOAD_DIR=%CD%\data\uploads
set EXPORT_DIR=%CD%\data\exports
set FILE_RETENTION_DAYS=30
set LOG_LEVEL=INFO
set LOG_FILE=%CD%\logs\app.log

echo OK Environment variables configured
echo    - API Port: %API_PORT%
echo    - AssetRipper Path: %ASSETRIPPER_PATH%
echo    - Database: %CD%\data\db\assetripper.db

REM Start service
echo.
echo [7/7] Starting AssetRipper API Server...
echo.
echo ========================================
echo   Service started successfully!
echo ========================================
echo.
echo Access URLs:
echo   - API Root:       http://localhost:%API_PORT%
echo   - API Docs:       http://localhost:%API_PORT%/docs
echo   - Health Check:   http://localhost:%API_PORT%/api/v1/health
echo.
echo Log file: %CD%\logs\app.log
echo.
echo Press Ctrl+C to stop the service
echo.

REM Start uvicorn
python -m uvicorn app.main:app --host %API_HOST% --port %API_PORT% --log-level info --reload
