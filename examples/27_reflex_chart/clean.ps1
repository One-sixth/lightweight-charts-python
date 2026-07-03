param(
    [switch]$FrontendOnly
)

$root = Split-Path -Parent $PSCommandPath

Write-Host "Cleaning Reflex cache in: $root" -ForegroundColor Cyan

# remove generated frontend
$dirs = @(
    "$root\.states"
)

# Clean .web folder but preserve node_modules and package.json
$webDir = "$root\.web"
if (Test-Path -LiteralPath $webDir) {
    Write-Host "  Cleaning: $webDir (preserving node_modules and package.json)" -ForegroundColor Yellow

    # Get all items in .web folder
    Get-ChildItem -LiteralPath $webDir | ForEach-Object {
        # Skip node_modules folder and package.json
        if ($_.Name -eq 'node_modules') {
            Write-Host "    Preserving: $($_.FullName)" -ForegroundColor DarkGreen
        } elseif ($_.Name -eq 'package.json') {
            Write-Host "    Preserving: $($_.FullName)" -ForegroundColor DarkGreen
        } else {
            Write-Host "    Removing: $($_.FullName)" -ForegroundColor Yellow
            Remove-Item -LiteralPath $_.FullName -Recurse -Force
        }
    }
} else {
    Write-Host "  Skipping (not found): $webDir" -ForegroundColor DarkGray
}

# remove Python cache
if (-not $FrontendOnly) {
    $dirs += @(
        "$root\__pycache__",
        "$root\rx_chart\__pycache__"
    )
}

foreach ($d in $dirs) {
    if (Test-Path -LiteralPath $d) {
        Write-Host "  Removing: $d" -ForegroundColor Yellow
        Remove-Item -LiteralPath $d -Recurse -Force
    } else {
        Write-Host "  Skipping (not found): $d" -ForegroundColor DarkGray
    }
}

Write-Host "Done." -ForegroundColor Green
