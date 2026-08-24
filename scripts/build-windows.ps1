[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $projectRoot
try {
    if (-not $SkipInstall) {
        & $Python -m pip install --upgrade pip
        & $Python -m pip install ".[build]"
    }

    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name osu-tracker `
        --icon images/osu-tracker.ico `
        --add-data "images/osu-tracker.ico;images" `
        --add-data "assets/azure;assets/azure" `
        --add-data "assets/fonts;assets/fonts" `
        --collect-all pydantic `
        --collect-all pypresence `
        OsuTracker/__main__.py

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    Write-Host "Build complete: $projectRoot\dist\osu-tracker.exe"
}
finally {
    Pop-Location
}
