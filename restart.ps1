# AssetRipper API Server - Windows Restart Script
# Stop current service and restart it

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

# Banner
Write-Color "========================================" -Color Blue
Write-Color "  AssetRipper API Server - Restart" -Color Blue
Write-Color "========================================" -Color Blue
Write-Host ""

# Stop service
Write-Step "Step 1/2: Stopping current service"
Write-Host ""
& "$PSScriptRoot\stop.ps1"

Write-Host ""
Write-Step "Step 2/2: Starting service"
Write-Host ""
Start-Sleep -Seconds 1

# Start service in daemon mode
& "$PSScriptRoot\start.ps1" -Daemon
