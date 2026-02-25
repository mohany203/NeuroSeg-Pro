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
echo ==========================================
echo PyTorch Installation Type
echo ==========================================
echo The application can run using your GPU (NVIDIA CUDA) or your CPU.
echo  - GPU (CUDA) is much faster but requires a compatible NVIDIA graphics card.
echo  - CPU works on all computers but is slower.
echo.
set /p INSTALL_CUDA="Do you want to install the GPU (CUDA) version? (Y/N): "

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip

if /I "%INSTALL_CUDA%"=="Y" goto InstallCUDA
goto InstallCPU

:InstallCUDA
echo.
echo Checking for NVIDIA CUDA Compiler (nvcc)...
nvcc --version >nul 2>&1
if !errorLevel! equ 0 (
    echo CUDA detected. Installing PyTorch for CUDA 12.1...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
    if !errorLevel! neq 0 (
        echo Failed to install CUDA PyTorch. Falling back to CPU version...
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    )
) else (
    echo CUDA (nvcc) not found on system path. Please ensure NVIDIA drivers and CUDA Toolkit are installed.
    echo Falling back to CPU version of PyTorch...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
)
goto FinishedPyTorch

:InstallCPU
echo.
echo Installing PyTorch (CPU Version)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
goto FinishedPyTorch

:FinishedPyTorch
if %errorLevel% neq 0 (
    echo Failed to install PyTorch.
    pause
    exit /b
)

echo.
echo Installing Other Requirements...
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo Failed to install requirements.
    pause
    exit /b
)

echo.
echo Setting up Icon...
python -c "from PIL import Image; import os; icon_path='assets/NeuroSeg_App_Icon.png'; ico_path='assets/NeuroSeg_App_Icon.ico'; Image.open(icon_path).save(ico_path, format='ICO', sizes=[(256, 256)]) if os.path.exists(icon_path) and not os.path.exists(ico_path) else None"

echo Creating Desktop and Local Shortcuts...
set "TARGET_PATH=%~dp0run_app.bat"
set "ICON_PATH=%~dp0assets\NeuroSeg_App_Icon.ico"
set "WORK_DIR=%~dp0"

:: PowerShell script to create shortcuts on both Desktop and the Installation Folder
powershell -Command "$desktop = [Environment]::GetFolderPath('Desktop'); $wshell = New-Object -ComObject WScript.Shell; $shortcutDesktop = $wshell.CreateShortcut((Join-Path $desktop 'NeuroSeg-Pro.lnk')); $shortcutDesktop.TargetPath = '%TARGET_PATH%'; $shortcutDesktop.WorkingDirectory = '%WORK_DIR%'; $shortcutDesktop.IconLocation = '%ICON_PATH%'; $shortcutDesktop.Save(); $shortcutLocal = $wshell.CreateShortcut((Join-Path '%WORK_DIR%' 'NeuroSeg-Pro.lnk')); $shortcutLocal.TargetPath = '%TARGET_PATH%'; $shortcutLocal.WorkingDirectory = '%WORK_DIR%'; $shortcutLocal.IconLocation = '%ICON_PATH%'; $shortcutLocal.Save()"

if %errorLevel% equ 0 (
    echo Shortcuts created successfully on Desktop and in the NeuroSeg-Pro folder.
) else (
    echo Failed to create shortcuts.
)

echo.
echo ==========================================
echo Setup Completed Successfully!
echo You can now run NeuroSeg-Pro using the shortcut on your desktop.
echo Remember to place your model files in the 'models/' directory.
echo ==========================================
pause
