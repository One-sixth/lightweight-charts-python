param(
    [switch]$FrontendOnly
)

$root = Split-Path -Parent $PSCommandPath

Write-Host "Cleaning Reflex cache in: $root" -ForegroundColor Cyan

# remove generated frontend
$dirs = @(
    "$root\.web",
    "$root\.states"
)

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
