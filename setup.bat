@echo off
setlocal enabledelayedexpansion

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

echo ==========================================
echo NeuroSeg-Pro Setup
echo ==========================================
echo.

cd /d "%~dp0"

:: Check Python installation
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.8+ and try again.
    pause
    exit /b
)

echo Creating Virtual Environment...
if not exist ".venv" (
    python -m venv .venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

echo.
echo Installing Requirements...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo Failed to install requirements.
    pause
    exit /b
)

echo.
echo Setting up Icon...
python -c "from PIL import Image; import os; icon_path='assets/NeuroSeg_App_Icon.png'; ico_path='assets/NeuroSeg_App_Icon.ico'; Image.open(icon_path).save(ico_path, format='ICO', sizes=[(256, 256)]) if os.path.exists(icon_path) and not os.path.exists(ico_path) else None"

echo Creating Desktop Shortcut...
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\NeuroSeg-Pro.lnk"
set "TARGET_PATH=%~dp0run_app.bat"
set "ICON_PATH=%~dp0assets\NeuroSeg_App_Icon.ico"
set "WORK_DIR=%~dp0"

:: PowerShell script to create the shortcut
powershell -Command "$wshell = New-Object -ComObject WScript.Shell; $shortcut = $wshell.CreateShortcut('%SHORTCUT_PATH%'); $shortcut.TargetPath = '%TARGET_PATH%'; $shortcut.WorkingDirectory = '%WORK_DIR%'; $shortcut.IconLocation = '%ICON_PATH%'; $shortcut.Save()"

if %errorLevel% equ 0 (
    echo Shortcut created on Desktop.
) else (
    echo Failed to create shortcut.
)

echo.
echo ==========================================
echo Setup Completed Successfully!
echo You can now run NeuroSeg-Pro using the shortcut on your desktop.
echo Remember to place your model files in the 'models/' directory.
echo ==========================================
pause
