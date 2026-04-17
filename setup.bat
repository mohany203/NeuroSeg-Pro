@echo off
setlocal

:: Elevate to Administrator if not already
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges to install NeuroSeg-Pro...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

:: Run the PowerShell installer script bypassing execution policy
cd /d "%~dp0"
echo Launching NeuroSeg-Pro Installer...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

endlocal
