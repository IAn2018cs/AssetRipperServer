# AssetRipper API Server - Windows Startup Script
# For running the service locally on Windows (without Docker)
#
# Usage:
#   .\start.ps1          - Start in foreground (occupies terminal)
#   .\start.ps1 -Daemon  - Start in background (daemon mode)

param(
    [switch]$Daemon = $false
)

# Color functions
function Write-Color {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

function Write-Step {
    param([string]$Text)
    Write-Color $Text -Color Yellow
}

function Write-Success {
    param([string]$Text)
    Write-Color $Text -Color Green
}

function Write-Error {
    param([string]$Text)
    Write-Host $Text -ForegroundColor Red
}

function Write-Info {
    param([string]$Text)
    Write-Color $Text -Color Cyan
}

# Banner
Write-Color "========================================" -Color Blue
if ($Daemon) {
    Write-Color "  AssetRipper API Server - Background Mode" -Color Blue
} else {
    Write-Color "  AssetRipper API Server - Foreground Mode" -Color Blue
}
Write-Color "========================================" -Color Blue
Write-Host ""

# [1/7] Check Python
Write-Step "[1/7] Checking Python environment..."
try {
    $pythonVersion = & python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Success "✓ Python version: $pythonVersion"
} catch {
    Write-Error "Error: Python 3.11+ not found. Please install Python first."
    exit 1
}

# Check if in project root
if (-not (Test-Path "requirements.txt")) {
    Write-Error "Error: Please run this script from the project root directory"
    exit 1
}

# [2/7] Setup virtual environment
Write-Host ""
Write-Step "[2/7] Setting up Python virtual environment..."
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    & python -m venv .venv
    Write-Success "✓ Virtual environment created"
} else {
    Write-Success "✓ Virtual environment already exists"
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
$activateScript = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
} else {
    Write-Error "Error: Cannot find activation script at $activateScript"
    exit 1
}

# [3/7] Install dependencies
Write-Host ""
Write-Step "[3/7] Installing Python dependencies..."
& python -m pip install --quiet --upgrade pip
& pip install --quiet -r requirements.txt
Write-Success "✓ Dependencies installed"

# [4/7] Check AssetRipper binary
Write-Host ""
Write-Step "[4/7] Checking AssetRipper binary..."
$assetRipperPath = $null

if (Test-Path "local\AssetRipper.GUI.Free.exe") {
    $assetRipperPath = Join-Path $PSScriptRoot "local\AssetRipper.GUI.Free.exe"
    Write-Success "✓ Found Windows version: local\AssetRipper.GUI.Free.exe"
} elseif (Test-Path "bin\AssetRipper.GUI.Free.exe") {
    $assetRipperPath = Join-Path $PSScriptRoot "bin\AssetRipper.GUI.Free.exe"
    Write-Success "✓ Found Windows version: bin\AssetRipper.GUI.Free.exe"
} else {
    Write-Error "Error: AssetRipper.GUI.Free.exe not found"
    Write-Host ""
    Write-Host "Please place the Windows version of AssetRipper.GUI.Free.exe in one of:"
    Write-Host "  1. local\AssetRipper.GUI.Free.exe (recommended)"
    Write-Host "  2. bin\AssetRipper.GUI.Free.exe"
    Write-Host ""
    Write-Host "Download: https://github.com/AssetRipper/AssetRipper/releases"
    exit 1
}

# [5/7] Create directories
Write-Host ""
Write-Step "[5/7] Creating data directories..."
$dirs = @("data\uploads", "data\exports", "data\db", "logs")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Success "✓ Directories created"

# [6/7] Set environment variables
Write-Host ""
Write-Step "[6/7] Configuring environment variables..."
$env:ENVIRONMENT = "development"
$env:API_HOST = "0.0.0.0"
$env:API_PORT = "8000"
$env:ASSETRIPPER_PORT = "8765"
$env:ASSETRIPPER_BINARY_PATH = $assetRipperPath
$env:DATABASE_URL = "sqlite+aiosqlite:///$($PSScriptRoot)\data\db\assetripper.db" -replace '\\', '/'
$env:UPLOAD_DIR = Join-Path $PSScriptRoot "data\uploads"
$env:EXPORT_DIR = Join-Path $PSScriptRoot "data\exports"
$env:FILE_RETENTION_DAYS = "30"
$env:LOG_LEVEL = "INFO"
$env:LOG_FILE = Join-Path $PSScriptRoot "logs\app.log"

Write-Success "✓ Environment variables configured"
Write-Host "   - API Port: $($env:API_PORT)"
Write-Host "   - AssetRipper Path: $assetRipperPath"
Write-Host "   - Database: $($PSScriptRoot)\data\db\assetripper.db"

# [7/7] Start service
Write-Host ""
Write-Step "[7/7] Starting AssetRipper API Server..."

if ($Daemon) {
    # Background mode
    Write-Host ""
    Write-Success "========================================"
    Write-Success "  Starting service in background..."
    Write-Success "========================================"
    Write-Host ""

    # Start process in background
    $logFile = Join-Path $PSScriptRoot "logs\uvicorn.log"
    $pidFile = Join-Path $PSScriptRoot "logs\uvicorn.pid"

    $processArgs = @(
        "-m", "uvicorn",
        "app.main:app",
        "--host", $env:API_HOST,
        "--port", $env:API_PORT,
        "--log-level", "info"
    )

    $process = Start-Process -FilePath "python" -ArgumentList $processArgs `
        -RedirectStandardOutput $logFile `
        -RedirectStandardError $logFile `
        -WindowStyle Hidden `
        -PassThru

    # Save PID
    $process.Id | Out-File -FilePath $pidFile -Encoding ASCII

    Write-Host "Waiting for service to start..."
    Start-Sleep -Seconds 3

    # Check if process is still running
    if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
        Write-Host ""
        Write-Success "✓ Service started successfully in background!"
        Write-Host ""
        Write-Info "Process ID: $($process.Id)"
        Write-Host ""
        Write-Host "Access URLs:"
        Write-Info "  - API Root:       http://localhost:$($env:API_PORT)"
        Write-Info "  - API Docs:       http://localhost:$($env:API_PORT)/docs"
        Write-Info "  - Health Check:   http://localhost:$($env:API_PORT)/api/v1/health"
        Write-Host ""
        Write-Host "Log files:"
        Write-Info "  - App Log:        $($PSScriptRoot)\logs\app.log"
        Write-Info "  - Uvicorn Log:    $logFile"
        Write-Host ""
        Write-Host "Management commands:"
        Write-Info "  - View logs:      Get-Content logs\uvicorn.log -Wait"
        Write-Info "  - Stop service:   .\stop.ps1"
        Write-Info "  - Restart:        .\restart.ps1"
        Write-Host ""
    } else {
        Write-Error "✗ Service failed to start"
        Write-Host "Please check logs: $logFile"
        exit 1
    }
} else {
    # Foreground mode
    Write-Host ""
    Write-Success "========================================"
    Write-Success "  Service started successfully!"
    Write-Success "========================================"
    Write-Host ""
    Write-Host "Access URLs:"
    Write-Info "  - API Root:       http://localhost:$($env:API_PORT)"
    Write-Info "  - API Docs:       http://localhost:$($env:API_PORT)/docs"
    Write-Info "  - Health Check:   http://localhost:$($env:API_PORT)/api/v1/health"
    Write-Host ""
    Write-Host "Log file: $($PSScriptRoot)\logs\app.log"
    Write-Host ""
    Write-Color "Press Ctrl+C to stop the service" -Color Yellow
    Write-Host ""

    # Start uvicorn in foreground
    & python -m uvicorn app.main:app `
        --host $env:API_HOST `
        --port $env:API_PORT `
        --log-level info `
        --reload
}
