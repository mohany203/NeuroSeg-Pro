<#
.SYNOPSIS
    Installs NeuroSeg-Pro on Windows natively.
.DESCRIPTION
    Checks for administrator privileges.
    Installs Visual C++ Redistributable if needed.
    Installs Python if needed, avoiding Windows Store aliases.
    Creates a python virtual environment.
    Detects NVIDIA GPUs via WMI.
    Installs the correct version of PyTorch (CUDA vs CPU).
    Installs requirements.txt.
#>

param()

$ErrorActionPreference = "Stop"
$WorkingDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------

function Write-Log {
    param([string]$Message, [string]$Level="INFO")
    $TimeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogLine = "[$TimeStamp] [$Level] $Message"
    Write-Host $LogLine
}

function Test-Administrator {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-Administrator {
    if (-not (Test-Administrator)) {
        Write-Log "This script requires Administrator privileges to install prerequisites." "WARNING"
        Write-Log "Attempting to elevate..." "INFO"
        
        $ArgumentList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        Start-Process PowerShell -ArgumentList $ArgumentList -Verb RunAs
        exit
    }
}

# -----------------------------------------------------------------------------
# Main Script Execution
# -----------------------------------------------------------------------------

try {
    Write-Log "=========================================="
    Write-Log "Starting NeuroSeg-Pro Installation"
    Write-Log "Working Directory: $WorkingDir"
    Write-Log "=========================================="

    Ensure-Administrator

    Set-Location $WorkingDir

    # 1. Install VC++ Redistributable
    Write-Log "Checking for Microsoft Visual C++ Redistributable..."
    $vcRedistInstalled = $false
    $uninstallKeys = @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*", "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*")
    foreach ($key in Get-ItemProperty $uninstallKeys -ErrorAction SilentlyContinue) {
        if ($key.DisplayName -match "Microsoft Visual C\+\+ 2015-2022 Redistributable \(x64\)") {
            $vcRedistInstalled = $true
            break
        }
    }

    if (-not $vcRedistInstalled) {
        Write-Log "Visual C++ Redistributable not found. Downloading..."
        $vcRedistUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
        $vcRedistInstaller = Join-Path $env:TEMP "vc_redist.x64.exe"
        Invoke-WebRequest -Uri $vcRedistUrl -OutFile $vcRedistInstaller -UseBasicParsing
        
        Write-Log "Installing Visual C++ Redistributable..."
        $process = Start-Process -FilePath $vcRedistInstaller -ArgumentList "/install /quiet /norestart" -Wait -PassThru
        if ($process.ExitCode -eq 0 -or $process.ExitCode -eq 3010 -or $process.ExitCode -eq 1638) {
            Write-Log "Visual C++ Redistributable installed successfully (or already present)."
        } else {
            Write-Log "Failed to install VC++ Redistributable. Exit code: $($process.ExitCode). Continuing anyway..." "WARNING"
        }
        Remove-Item $vcRedistInstaller -Force -ErrorAction SilentlyContinue
    } else {
        Write-Log "Visual C++ Redistributable is already installed."
    }

    # 2. Check and Install Python
    Write-Log "Checking for Python..."
    $pythonExe = "python.exe"
    $pythonCmd = Get-Command $pythonExe -ErrorAction SilentlyContinue

    if ($pythonCmd -and $pythonCmd.Source -match "WindowsApps") {
        Write-Log "Found Windows Store Python alias instead of real Python. Ignoring dummy alias..." "WARNING"
        $pythonCmd = $null
    }

    if (-not $pythonCmd) {
        Write-Log "Python 3 is not properly installed or not in PATH."
        Write-Log "Downloading Python 3.11.8 installer (this may take a minute)..."
        $pythonInstallerUrl = "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe"
        $pythonInstallerPath = Join-Path $env:TEMP "python-installer.exe"
        Invoke-WebRequest -Uri $pythonInstallerUrl -OutFile $pythonInstallerPath -UseBasicParsing
        
        Write-Log "Installing Python system-wide..."
        $installArgs = "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"
        $process = Start-Process -FilePath $pythonInstallerPath -ArgumentList $installArgs -Wait -PassThru
        
        if ($process.ExitCode -eq 0) {
            Write-Log "Python installed successfully."
            # Refresh environment variables
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
            $pythonExe = "python.exe"
        } else {
            Write-Log "Failed to install Python natively. Exit Code: $($process.ExitCode)" "ERROR"
            throw "Python installation failed."
        }
        Remove-Item $pythonInstallerPath -Force -ErrorAction SilentlyContinue
    } else {
        Write-Log "Found Python at $($pythonCmd.Source)"
    }

    # Verify python responds
    $pyVersion = & $pythonExe --version 2>&1
    Write-Log "Using Python Version: $pyVersion"

    # 3. Create Virtual Environment
    $venvPath = Join-Path $WorkingDir ".venv"
    $pythonVenvPath = Join-Path $venvPath "Scripts\python.exe"
    if (-not (Test-Path $pythonVenvPath)) {
        Write-Log "Creating virtual environment at $venvPath..."
        if (Test-Path $venvPath) {
            Write-Log "Found empty or corrupted .venv directory. Removing it..."
            Remove-Item -Recurse -Force $venvPath -ErrorAction SilentlyContinue
        }
        & $pythonExe -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment! Check if python venv module is working."
        }
    } else {
        Write-Log "Virtual environment already exists."
    }

    # 4. Activate Venv and Upgrade Pip
    $pythonVenvPath = Join-Path $venvPath "Scripts\python.exe"
    $pipVenvPath = Join-Path $venvPath "Scripts\pip.exe"

    if (-not (Test-Path $pythonVenvPath)) {
        throw "Virtual environment python.exe not found at $pythonVenvPath"
    }

    Write-Log "Upgrading pip (this may take a moment)..."
    & $pythonVenvPath -m pip install --upgrade pip

    # 5. Detect NVIDIA GPU
    Write-Log "Detecting Graphics Capabilities..."
    $hasNvidiaGPU = $false
    try {
        $videoControllers = Get-CimInstance Win32_VideoController
        foreach ($gpu in $videoControllers) {
            if ($gpu.Name -match "NVIDIA") {
                Write-Log "Found NVIDIA GPU: $($gpu.Name)"
                $hasNvidiaGPU = $true
                break
            }
        }
    } catch {
        Write-Log "Error querying GPUs: $_" "WARNING"
    }

    # 6. Check if PyTorch/heavy libraries are already installed to save bandwidth
    $skipTorch = $false
    $torchCheck = & $pythonVenvPath -c "import torch; print('INSTALLED')" 2>$null
    if ($torchCheck -eq "INSTALLED") {
        Write-Log "--------------------------------------------------------"
        Write-Log "Found existing PyTorch installation in the virtual environment."
        Write-Log "Automatically skipping PyTorch download to save bandwidth during update!"
        $skipTorch = $true
    }

    if (-not $skipTorch) {
        # 7. Install PyTorch visibly so the user sees the progress bar!
        if ($hasNvidiaGPU) {
            Write-Log "Installing PyTorch with CUDA 12.1 support (Warning: This is a ~3GB download, please be patient!)..."
            & $pipVenvPath install torch torchvision --index-url https://download.pytorch.org/whl/cu121
            if ($LASTEXITCODE -ne 0) {
                Write-Log "Failed to install CUDA PyTorch. Falling back to CPU..." "WARNING"
                $hasNvidiaGPU = $false
            }
        }

        if (-not $hasNvidiaGPU) {
            Write-Log "Installing PyTorch for CPU (Warning: This is a large download, please be patient!)..."
            & $pipVenvPath install torch torchvision --index-url https://download.pytorch.org/whl/cpu
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to install CPU PyTorch."
            }
        }
    } else {
        Write-Log "PyTorch download skipped."
    }

    # 8. Always verify and install/update Requirements
    Write-Log "Analyzing and updating application requirements..."
    $reqPath = Join-Path $WorkingDir "requirements.txt"
    if (Test-Path $reqPath) {
        & $pipVenvPath install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Failed to install some requirements!" "WARNING"
        } else {
            Write-Log "Requirements checked and updated successfully."
        }
    } else {
        Write-Log "requirements.txt not found!" "WARNING"
    }

    # 8. Setup Icon
    Write-Log "Generating Application Icon..."
    $iconSetupScript = "from PIL import Image; import os; icon_path='assets/NeuroSeg_App_Icon.png'; ico_path='assets/NeuroSeg_App_Icon.ico'; Image.open(icon_path).save(ico_path, format='ICO', sizes=[(256, 256)]) if os.path.exists(icon_path) and not os.path.exists(ico_path) else None"
    & $pythonVenvPath -c $iconSetupScript

    Write-Log "=========================================="
    Write-Log "Setup Completed Successfully!"
    Write-Log "You can now run NeuroSeg-Pro using the shortcut on your desktop."
    Write-Log "=========================================="

} catch {
    Write-Log "A FATAL ERROR OCCURRED DURING INSTALLATION!" "ERROR"
    Write-Log $_.Exception.Message "ERROR"
    Write-Log $_.InvocationInfo.PositionMessage "ERROR"
    exit 1
}

Write-Host "Press any key to close this installer window and finish setup..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
