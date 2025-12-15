# AssetRipper API Server - Windows Stop Script
# Stop the locally running service

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

function Write-Warning {
    param([string]$Text)
    Write-Color $Text -Color Yellow
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
Write-Color "  AssetRipper API Server - Stop Service" -Color Blue
Write-Color "========================================" -Color Blue
Write-Host ""

# [1/2] Stop uvicorn processes
Write-Step "[1/2] Finding uvicorn processes..."
$uvicornProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*app.main:app*"
}

if ($uvicornProcesses.Count -eq 0) {
    Write-Warning "⚠ No running uvicorn processes found"
} else {
    Write-Success "✓ Found uvicorn processes: $($uvicornProcesses.Id -join ', ')"
    Write-Host "Stopping uvicorn..."

    foreach ($proc in $uvicornProcesses) {
        try {
            Stop-Process -Id $proc.Id -Force
            Write-Host "  - Stopped process $($proc.Id)"
        } catch {
            Write-Warning "  - Failed to stop process $($proc.Id): $_"
        }
    }

    # Wait for processes to exit
    Start-Sleep -Seconds 2

    # Check for remaining processes
    $remaining = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*uvicorn*app.main:app*"
    }

    if ($remaining.Count -eq 0) {
        Write-Success "✓ uvicorn service stopped"
    } else {
        Write-Warning "⚠ Some processes did not stop cleanly"
        Write-Host "Remaining processes: $($remaining.Id -join ', ')"
    }
}

# [2/2] Stop AssetRipper processes
Write-Host ""
Write-Step "[2/2] Finding AssetRipper processes..."
$assetRipperProcesses = Get-Process -Name "AssetRipper.GUI.Free" -ErrorAction SilentlyContinue

if ($assetRipperProcesses.Count -eq 0) {
    Write-Warning "⚠ No running AssetRipper processes found"
} else {
    Write-Success "✓ Found AssetRipper processes: $($assetRipperProcesses.Id -join ', ')"
    Write-Host "Stopping AssetRipper..."

    foreach ($proc in $assetRipperProcesses) {
        try {
            Stop-Process -Id $proc.Id -Force
            Write-Host "  - Stopped process $($proc.Id)"
        } catch {
            Write-Warning "  - Failed to stop process $($proc.Id): $_"
        }
    }

    # Wait for processes to exit
    Start-Sleep -Seconds 2

    # Check for remaining processes
    $remaining = Get-Process -Name "AssetRipper.GUI.Free" -ErrorAction SilentlyContinue

    if ($remaining.Count -eq 0) {
        Write-Success "✓ AssetRipper processes stopped"
    } else {
        Write-Warning "⚠ Some processes did not stop cleanly"
        Write-Host "Remaining processes: $($remaining.Id -join ', ')"
    }
}

# Display results
Write-Host ""
Write-Success "========================================"
Write-Success "  Service stop complete!"
Write-Success "========================================"
Write-Host ""

# Check if any processes are still running
$remainingUvicorn = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*app.main:app*"
}
$remainingAssetRipper = Get-Process -Name "AssetRipper.GUI.Free" -ErrorAction SilentlyContinue

if ($remainingUvicorn.Count -eq 0 -and $remainingAssetRipper.Count -eq 0) {
    Write-Success "✓ All services completely stopped"
} else {
    Write-Warning "⚠ Warning: Some processes are still running"
    if ($remainingUvicorn.Count -gt 0) {
        Write-Host "  - uvicorn: $($remainingUvicorn.Id -join ', ')"
    }
    if ($remainingAssetRipper.Count -gt 0) {
        Write-Host "  - AssetRipper: $($remainingAssetRipper.Id -join ', ')"
    }
    Write-Host ""
    Write-Host "To force kill, run:"
    Write-Info '  Stop-Process -Name "python" -Force'
    Write-Info '  Stop-Process -Name "AssetRipper.GUI.Free" -Force'
}

Write-Host ""
