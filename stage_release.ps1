<#
.SYNOPSIS
    Stages NeuroSeg Pro v4.0.0 production runtime artifacts into the release/ directory.
#>
$ErrorActionPreference = "Stop"
$WorkingDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ReleaseDir = Join-Path $WorkingDir "release"

Write-Host "Staging NeuroSeg Pro v4.0.0 release directory..."
if (Test-Path $ReleaseDir) { Remove-Item -Recurse -Force $ReleaseDir }
New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null

Copy-Item -Path (Join-Path $WorkingDir "NeuroSegPro.vbs") -Destination $ReleaseDir -Force
Copy-Item -Path (Join-Path $WorkingDir "install.ps1") -Destination $ReleaseDir -Force

$ReqFile = Join-Path $WorkingDir "requirements.txt"
if (Test-Path $ReqFile) {
    Copy-Item -Path $ReqFile -Destination $ReleaseDir -Force
}

$AssetsDest = Join-Path $ReleaseDir "assets"
Copy-Item -Path (Join-Path $WorkingDir "assets") -Destination $AssetsDest -Recurse -Force

$AppDest = Join-Path $ReleaseDir "app"
Copy-Item -Path (Join-Path $WorkingDir "app") -Destination $AppDest -Recurse -Force

# Clean up pycache inside staged app folder
Get-ChildItem -Path $ReleaseDir -Include "__pycache__" -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $ReleaseDir -Include "*.pyc", "*.log" -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "Successfully staged production artifacts into: $ReleaseDir"
