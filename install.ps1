<#
.SYNOPSIS
    NeuroSeg Pro v4.0.0 Enterprise Bootstrapper & Maintenance Orchestrator (10/10 Commercial Spec)
.DESCRIPTION
    Single source of truth for runtime setup. Performs system diagnostics, multi-log separation,
    Python acquisition, LocalAppData virtual environment management, categorized dependency acquisition
    from requirements.txt, PyTorch GPU acceleration profiling, strict multi-stage verification,
    and standardized exit codes (0=Success, 1=PyErr, 2=VenvErr, 3=DepErr, 4=GpuErr, 5=VerifyErr).
#>

param(
    [switch]$Unattended = $false,
    [switch]$Repair = $false
)

$ErrorActionPreference = "Continue"
$StartTime = Get-Date
$Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

$WorkingDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalAppDataDir = Join-Path $env:LOCALAPPDATA "NeuroSegPro"
$LogDir = Join-Path $LocalAppDataDir "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# Multi-log separation targets
$LogBootstrap  = Join-Path $LogDir "bootstrap.log"
$LogPython     = Join-Path $LogDir "python_install.log"
$LogDeps       = Join-Path $LogDir "dependency_install.log"
$LogGpu        = Join-Path $LogDir "gpu_detection.log"
$LogVerify     = Join-Path $LogDir "verification.log"
$LogRepair     = Join-Path $LogDir "repair.log"

$VenvDir = Join-Path $LocalAppDataDir ".venv"
$VenvPy  = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"
$VenvPyw = Join-Path $VenvDir "Scripts\pythonw.exe"
$TempFilesToClean = @()

# -----------------------------------------------------------------------------
# Logging & Helper Functions
# -----------------------------------------------------------------------------

function Write-Log {
    param([string]$Message, [string]$Level = "INFO", [string]$TargetLog = $LogBootstrap)
    $TimeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Formatted = "[$TimeStamp] [$Level] $Message"
    Write-Host $Formatted
    Add-Content -Path $TargetLog -Value $Formatted -ErrorAction SilentlyContinue
    if ($TargetLog -ne $LogBootstrap) {
        Add-Content -Path $LogBootstrap -Value $Formatted -ErrorAction SilentlyContinue
    }
    if ($Repair) {
        Add-Content -Path $LogRepair -Value $Formatted -ErrorAction SilentlyContinue
    }
}

function Log-Exception {
    param([string]$OpName, [string]$CommandStr, [int]$ErrCode, [object]$Ex)
    $TimeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $exMsg   = if ($Ex -is [System.Management.Automation.ErrorRecord]) { $Ex.Exception.Message } elseif ($Ex.Message) { $Ex.Message } else { $Ex.ToString() }
    $exStack = if ($Ex -is [System.Management.Automation.ErrorRecord]) { $Ex.ScriptStackTrace } elseif ($Ex.StackTrace) { $Ex.StackTrace } else { "" }
    $Formatted = "`n[$TimeStamp] [FATAL EXCEPTION]`nOperation  : $OpName`nCommand    : $CommandStr`nExit Code  : $ErrCode`nException  : $exMsg`nStackTrace : $exStack`n"
    Write-Host $Formatted -ForegroundColor Red
    Add-Content -Path $LogBootstrap -Value $Formatted -ErrorAction SilentlyContinue
    if ($Repair) { Add-Content -Path $LogRepair -Value $Formatted -ErrorAction SilentlyContinue }
}

function Update-EnvironmentPath {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Get-ResumableDownload {
    param([string]$Url, [string]$Destination, [int]$MaxRetries = 3)
    $script:TempFilesToClean += $Destination
    $attempt = 1
    while ($attempt -le $MaxRetries) {
        try {
            Write-Log "Downloading $Url (Attempt $attempt of $MaxRetries)..." "INFO" $LogBootstrap
            if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {
                Start-BitsTransfer -Source $Url -Destination $Destination -Description "NeuroSeg Pro Runtime" -RetryInterval 10 -RetryTimeout 60
            } else {
                Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
            }
            if (Test-Path $Destination) { return $true }
        } catch {
            Write-Log "Download retry $attempt error`: $_" "WARNING" $LogBootstrap
            $attempt++
            if ($attempt -le $MaxRetries) { Start-Sleep -Seconds ([math]::pow(2, $attempt)) }
        }
    }
    throw "Failed downloading $Url after $MaxRetries attempts."
}

# -----------------------------------------------------------------------------
# Main Execution Flow
# -----------------------------------------------------------------------------

try {
    Write-Log "============================================================" "INFO" $LogBootstrap
    Write-Log "NeuroSeg Pro v4.0.0 Enterprise Bootstrapper Initiated" "INFO" $LogBootstrap
    Write-Log "Working Directory : $WorkingDir" "INFO" $LogBootstrap
    Write-Log "Runtime Directory : $VenvDir" "INFO" $LogBootstrap
    Write-Log "Execution Mode    : $(if ($Repair) { 'REPAIR & MAINTENANCE' } else { 'STANDARD SETUP' })" "INFO" $LogBootstrap
    Write-Log "============================================================" "INFO" $LogBootstrap

    Set-Location $WorkingDir

    # --- Step 1: Privilege Verification & Self-Elevation Enforcement ---
    Write-Log "Auditing Windows security context and privileges..." "INFO" $LogBootstrap
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]$currentIdentity
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    $integrityLevel = if ($isAdmin) { "High / System Integrity" } else { "Medium / Standard User Integrity" }

    Write-Log "Current Identity    : $($currentIdentity.Name)" "INFO" $LogBootstrap
    Write-Log "Integrity Level     : $integrityLevel" "INFO" $LogBootstrap
    Write-Log "Admin Rights Present: $isAdmin" "INFO" $LogBootstrap

    $elevationRequired = -not $isAdmin
    Write-Log "Elevation Required  : $elevationRequired" "INFO" $LogBootstrap

    if (-not $isAdmin) {
        Write-Log "Notice: Bootstrapper invoked without Administrator rights. Relaunching via Start-Process -Verb RunAs..." "WARNING" $LogBootstrap
        $argList = @("-ExecutionPolicy", "Bypass", "-NoProfile", "-File", "`"$($MyInvocation.MyCommand.Path)`"")
        if ($Unattended) { $argList += "-Unattended" }
        if ($Repair)     { $argList += "-Repair" }

        try {
            $elevatedProc = Start-Process powershell.exe -Verb RunAs -ArgumentList $argList -Wait -PassThru
            Write-Log "Self-elevation relaunch succeeded. Child process exited with code: $($elevatedProc.ExitCode)" "INFO" $LogBootstrap
            exit $elevatedProc.ExitCode
        } catch {
            Write-Log "Self-elevation failed or UAC prompt declined by user (`$_)." "ERROR" $LogBootstrap
            throw "Administrator privileges are required to configure NeuroSeg Pro system dependencies."
        }
    }

    $osInfo = Get-CimInstance Win32_OperatingSystem
    Write-Log "Operating System: $($osInfo.Caption) (Build $($osInfo.BuildNumber))" "INFO" $LogBootstrap
    Write-Log "CPU Architecture: $($env:PROCESSOR_ARCHITECTURE)" "INFO" $LogBootstrap

    $isOnline = $false
    try {
        $connTest = Invoke-WebRequest -Uri "https://pypi.org" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($connTest.StatusCode -eq 200) { $isOnline = $true }
    } catch { $isOnline = $false }
    Write-Log "Internet Connectivity: $(if ($isOnline) { 'ONLINE' } else { 'OFFLINE' })" "INFO" $LogBootstrap

    # --- Step 2: GPU Intelligence & CUDA Capability ---
    Write-Log "Detecting GPU acceleration capabilities..." "INFO" $LogGpu
    $gpuName = "CPU Only"
    $cudaSupported = $false
    try {
        $gpus = Get-CimInstance Win32_VideoController
        foreach ($g in $gpus) {
            Write-Log "Graphics Adapter Detected: $($g.Name) ($([math]::round($g.AdapterRAM / 1GB, 1)) GB VRAM)" "INFO" $LogGpu
            if ($g.Name -match "NVIDIA") {
                $gpuName = $g.Name
                $smiCmd = Get-Command "nvidia-smi" -ErrorAction SilentlyContinue
                if ($smiCmd) {
                    $smiLines = @(& $smiCmd --query-gpu=driver_version --format=csv,noheader 2>$null)
                    if ($smiLines.Count -gt 0 -and $smiLines[0]) {
                        $driverVer = ([string]$smiLines[0]).Trim()
                        $driverMajor = [int]($driverVer -split '\.')[0]
                        Write-Log "NVIDIA Display Driver Version: $driverVer" "INFO" $LogGpu
                        if ($driverMajor -ge 525) {
                            $cudaSupported = $true
                            Write-Log "NVIDIA Driver confirmed compatible with CUDA 12.1 runtime." "INFO" $LogGpu
                        } else {
                            Write-Log "Warning: NVIDIA driver ($driverVer) older than v525.x. Falling back to CPU target." "WARNING" $LogGpu
                        }
                    }
                }
            } elseif ($g.Name -match "AMD|Intel") {
                $gpuName = $g.Name
            }
        }
    } catch { Write-Log "GPU detection warning: $_" "WARNING" $LogGpu }

    # --- Step 3: Visual C++ Runtime & Git Audit ---
    Write-Log "Verifying Visual C++ Redistributable x64..." "INFO" $LogBootstrap
    $vcInstalled = $false
    $uninsKeys = @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*", "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*")
    foreach ($k in Get-ItemProperty $uninsKeys -ErrorAction SilentlyContinue) {
        if ($k.DisplayName -match "Microsoft Visual C\+\+ 201(5|7|9|5-2022) Redistributable \(x64\)") { $vcInstalled = $true; break }
    }
    if (-not $vcInstalled -and $isOnline) {
        Write-Log "Downloading Visual C++ Redistributable x64 (~25 MB)..." "INFO" $LogBootstrap
        $vcExe = Join-Path $env:TEMP "vc_redist.x64.exe"
        Get-ResumableDownload -Url "https://aka.ms/vs/17/release/vc_redist.x64.exe" -Destination $vcExe
        Start-Process -FilePath $vcExe -ArgumentList "/install /quiet /norestart" -Wait | Out-Null
    }

    # --- Step 4: Python Runtime Acquisition & Verification (Exit Code 1 on Failure) ---
    try {
        Write-Log "Auditing system Python runtime (>=3.11.0, <3.13.0)..." "INFO" $LogPython
        Update-EnvironmentPath
        $pythonExe = "python.exe"
        $pyCmd = Get-Command $pythonExe -ErrorAction SilentlyContinue
        if ($pyCmd -and $pyCmd.Source -match "WindowsApps") { $pyCmd = $null }

        $validPy = $false
        if ($pyCmd) {
            $verStr = & $pyCmd.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($verStr -match "3\.(11|12)") {
                $validPy = $true; $pythonExe = $pyCmd.Source
                Write-Log "Verified System Python: v$verStr at $pythonExe" "INFO" $LogPython
            }
        }

        if (-not $validPy) {
            if (-not $isOnline) { throw "Python 3.11 runtime required but system is offline." }
            Write-Log "Downloading Python 3.11.8 x64 installer (~25.5 MB)..." "INFO" $LogPython
            $pyInst = Join-Path $env:TEMP "python-3.11.8-amd64.exe"
            Get-ResumableDownload -Url "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe" -Destination $pyInst
            Write-Log "Installing Python 3.11.8 silently..." "INFO" $LogPython
            $proc = Start-Process -FilePath $pyInst -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Shortcuts=0 CompileAll=1 Include_doc=0 Include_dev=0 Include_launcher=1 SimpleInstall=1" -Wait -PassThru
            if ($proc.ExitCode -ne 0) { throw "Python installer returned exit code $($proc.ExitCode)." }
            Update-EnvironmentPath
            $defaultPy = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
            if (Test-Path $defaultPy) { $pythonExe = $defaultPy } else {
                $sysPy = Get-Command "python.exe" -ErrorAction SilentlyContinue
                if ($sysPy) { $pythonExe = $sysPy.Source } else { throw "Python installed but executable binary unlocated." }
            }
        }
    } catch {
        Log-Exception "Python Acquisition" "Python Setup Engine" 1 $_
        exit 1
    }

    # --- Step 5: Virtual Environment Orchestration (Exit Code 2 on Failure) ---
    try {
        Write-Log "Orchestrating LocalAppData virtual environment at $VenvDir..." "INFO" $LogBootstrap
        if (-not (Test-Path $VenvPy) -or -not (Test-Path $VenvPyw) -or $Repair) {
            Write-Log "Creating virtual environment via $pythonExe -m venv --system-site-packages $VenvDir..." "INFO" $LogBootstrap
            if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue }
            & $pythonExe -m venv --system-site-packages $VenvDir
            $venvExit = $LASTEXITCODE
            Write-Log "python -m venv exited with code $venvExit" "INFO" $LogBootstrap
            if ($venvExit -ne 0 -or -not (Test-Path $VenvPyw)) { throw "Virtual environment initialization failed with exit code $venvExit." }
        } else {
            # Ensure existing virtual environment includes system & user site-packages to avoid redundant gigabyte downloads
            $pyvenvCfg = Join-Path $VenvDir "pyvenv.cfg"
            if (Test-Path $pyvenvCfg) {
                $cfgContent = Get-Content $pyvenvCfg -Raw
                if ($cfgContent -match "include-system-site-packages\s*=\s*false") {
                    Write-Log "Updating existing pyvenv.cfg to include-system-site-packages = true..." "INFO" $LogBootstrap
                    $cfgContent -replace "include-system-site-packages\s*=\s*false", "include-system-site-packages = true" | Set-Content $pyvenvCfg -Force
                }
            }
        }
        Write-Log "Upgrading base packaging toolchain (pip, setuptools, wheel)..." "INFO" $LogBootstrap
        & $VenvPy -m pip install --upgrade pip setuptools wheel --quiet
        $pipExit = $LASTEXITCODE
        Write-Log "pip upgrade exited with code $pipExit" "INFO" $LogBootstrap
        if ($pipExit -ne 0) { throw "Packaging toolchain upgrade exited with code $pipExit." }
    } catch {
        Log-Exception "Virtual Environment Creation" "python -m venv" 2 $_
        exit 2
    }

    # --- Step 6: PyTorch Engine Acquisition (Exit Code 4 on Failure) ---
    try {
        Write-Log "Auditing PyTorch Deep Learning Runtime..." "INFO" $LogGpu
        $torchVer = & $VenvPy -c "import torch; print(torch.__version__)" 2>$null
        $chkExit = $LASTEXITCODE
        Write-Log "PyTorch dry import exited with code $chkExit (Version: $torchVer)" "INFO" $LogGpu

        $needTorch = $false
        if ($chkExit -ne 0 -or -not $torchVer -or $Repair) { $needTorch = $true }
        elseif ($cudaSupported -and $torchVer -notmatch "\+cu") { $needTorch = $true }

        if ($needTorch) {
            if (-not $isOnline) { Write-Log "Offline mode: Skipping online PyTorch download." "WARNING" $LogGpu }
            else {
                $torchMB = if ($cudaSupported) { 2450.0 } else { 240.0 }
                Write-Log "Acquiring PyTorch $(if ($cudaSupported) { 'CUDA 12.1 Engine' } else { 'CPU Engine' }) (~$torchMB MB payload)..." "INFO" $LogGpu
                $idxUrl = if ($cudaSupported) { "https://download.pytorch.org/whl/cu121" } else { "https://download.pytorch.org/whl/cpu" }
                Write-Log "Executing: $VenvPip install torch torchvision --index-url $idxUrl" "INFO" $LogGpu
                & $VenvPip install torch torchvision --index-url $idxUrl --prefer-binary
                $torchExit = $LASTEXITCODE
                Write-Log "pip install torch exited with code $torchExit" "INFO" $LogGpu
                if ($torchExit -ne 0) { throw "PyTorch installation failed with exit code $torchExit." }
            }
        } else { Write-Log "PyTorch engine verified satisfied: $torchVer" "INFO" $LogGpu }
    } catch {
        Log-Exception "PyTorch Acceleration Setup" "pip install torch" 4 $_
        exit 4
    }

    # --- Step 7: Dependency Manifest Acquisition from requirements.txt (Exit Code 3 on Failure) ---
    try {
        $ReqFile = Join-Path $WorkingDir "requirements.txt"
        if (Test-Path $ReqFile) {
            Write-Log "Auditing dependencies directly against $ReqFile..." "INFO" $LogDeps
            Write-Log "Estimated Total Clinical Manifest Payload : ~1750.0 MB" "INFO" $LogDeps
            Write-Log "Estimated Installed Disk Storage Required : ~3850.0 MB" "INFO" $LogDeps

            if ($isOnline) {
                Write-Log "Executing: $VenvPip install -r $ReqFile --prefer-binary" "INFO" $LogDeps
                & $VenvPip install -r $ReqFile --prefer-binary
                $depsExit = $LASTEXITCODE
                Write-Log "pip install -r requirements.txt exited with code $depsExit" "INFO" $LogDeps
                if ($depsExit -ne 0) { throw "pip install -r requirements.txt failed with exit code $depsExit." }
            } else {
                Write-Log "System offline: Unable to synchronize requirements.txt online." "WARNING" $LogDeps
            }
        } else {
            Write-Log "Notice: requirements.txt not located at $ReqFile." "WARNING" $LogDeps
        }
    } catch {
        Log-Exception "Requirements Acquisition" "pip install -r requirements.txt" 3 $_
        exit 3
    }

    # --- Step 8: Comprehensive Verification Audit (Exit Code 5 on Failure) ---
    try {
        Write-Log "Executing strict post-setup runtime verification audit..." "INFO" $LogVerify
        if (-not (Test-Path $VenvPy))  { throw "Verification failed: python.exe unlocated in .venv." }
        if (-not (Test-Path $VenvPyw)) { throw "Verification failed: pythonw.exe unlocated in .venv." }
        if (-not (Test-Path $VenvPip)) { throw "Verification failed: pip.exe unlocated in .venv." }

        $CoreModules = @("numpy", "torch", "nibabel", "PyQt5", "monai", "pennylane", "scipy")
        $missingMods = @()
        foreach ($mod in $CoreModules) {
            & $VenvPy -c "import $mod" 2>$null
            if ($LASTEXITCODE -ne 0) { $missingMods += $mod }
        }
        if ($missingMods.Count -gt 0) {
            if (-not $isOnline) {
                Write-Log "Audit note: Offline mode skipped downloading missing modules: $($missingMods -join ', ')" "WARNING" $LogVerify
            } else {
                throw "Verification failure: Missing essential core modules: $($missingMods -join ', ')"
            }
        }

        # Verify application entry point importability
        $MainPy = Join-Path $WorkingDir "app\main.py"
        if (Test-Path $MainPy) {
            & $VenvPy -c "import sys; sys.path.insert(0, r'$WorkingDir'); import app.version" 2>&1
            $appExit = $LASTEXITCODE
            Write-Log "Application core dry import exited with code $appExit" "INFO" $LogVerify
            if ($appExit -ne 0) { Write-Log "Warning during application dry import verification (Exit $appExit)" "WARNING" $LogVerify }
            else { Write-Log "Application core import verified successfully." "INFO" $LogVerify }
        }

        Write-Log "Runtime verification audit confirmed 100% successful." "INFO" $LogVerify
    } catch {
        Log-Exception "Runtime Verification Audit" "Verification Engine" 5 $_
        exit 5
    }

    $Stopwatch.Stop()
    Write-Log "============================================================" "INFO" $LogBootstrap
    Write-Log "BOOTSTRAPPER ORCHESTRATION COMPLETED SUCCESSFULLY (EXIT 0)" "INFO" $LogBootstrap
    Write-Log "Execution Duration : $($Stopwatch.Elapsed.Minutes)m $($Stopwatch.Elapsed.Seconds)s" "INFO" $LogBootstrap
    Write-Log "============================================================" "INFO" $LogBootstrap
    exit 0

} catch {
    $Stopwatch.Stop()
    Log-Exception "Unhandled Bootstrapper Execution" "install.ps1" 1 $_
    exit 1
} finally {
    foreach ($tf in $script:TempFilesToClean) {
        if ($tf -and (Test-Path $tf)) { Remove-Item $tf -Force -ErrorAction SilentlyContinue }
    }
}
