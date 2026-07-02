# Changelog

All notable changes to **NeuroSeg Pro** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v4.0.0] - 2026-07-02

### Added
- **Intelligent Windows Bootstrapper (`install.ps1`)**: Single source of truth installer script with multi-stage system auditing, CPU/OS spec logging, and automatic setup of isolated `%LOCALAPPDATA%\NeuroSegPro\.venv` Python environments.
- **Multi-Log Split Telemetry**: Separate diagnostic log files generated under `%LOCALAPPDATA%\NeuroSegPro\logs`:
  - `bootstrap.log` (System initialization, privilege checks, environment setup)
  - `python_install.log` (Silent Python 3.11 acquisition and PATH registration)
  - `gpu_audit.log` (NVIDIA CUDA runtime detection, PyTorch Deep Learning Engine validation)
- **Smart System Package Reuse (`--system-site-packages`)**: Virtual environment creation now inherits visibility into system and user site-packages (`%APPDATA%\Python\Python311\site-packages`), skipping redundant multi-gigabyte PyTorch/MONAI downloads on pre-configured workstations.
- **Windowless Silent Launcher (`NeuroSegPro.vbs`)**: Replaced legacy console batch scripts with a clean VBS launcher executing via `wscript.exe` and `pythonw.exe`, eliminating terminal popup windows on startup.
- **Interactive Self-Healing & Repair Tool**: Automatically detects missing runtime components or corrupted environments and prompts users with a graphical dialog to run `install.ps1 -Repair`.
- **Advanced Clinical Post-Processing**: Sigmoid-based hierarchical thresholding (`> 0.5`) with strict priority assignment (`ET (3) > TC/NCR (1) > WT/ED (2)`).
- **Automated Staging Pipeline (`stage_release.ps1`)**: Powershell script to stage runtime scripts, application modules, requirements, and assets cleanly into the production `release/` bundle prior to compilation.

### Changed
- **Architectural Fix in `DynUNet`**: Updated classical bottleneck (`self.bottleneck`) spatial stride from `stride=1` to `stride=2`. This aligns 3D tensor spatial dimensions across all 6 decoder upsampling stages ($S/64 \rightarrow S/32 \rightarrow S/16 \rightarrow S/8 \rightarrow S/4 \rightarrow S/2 \rightarrow S$), eliminating `RuntimeError: Sizes of tensors must match except in dimension 1` during 3D sliding-window inference.
- **Inno Setup Configuration (`installer.iss`)**: Enforced strict Administrator privileges (`PrivilegesRequired=admin`, `PrivilegesRequiredOverridesAllowed=none`), shifted bootstrapper execution to `CurStepChanged(ssPostInstall)` for precise exit code verification, and registered `.nii` / `.nii.gz` shell file associations directly to `wscript.exe`.
- **Inference Optimization**: Standardized sliding-window patch resolution (`roi_size=(128, 128, 128)`) with `0.5` overlap and Gaussian weighting to prevent destructive whole-volume downsampling on large clinical scans.

### Fixed
- Fixed Win32 CreateProcess Error 193 when launching `.vbs` files from Inno Setup shortcuts by specifying `{sys}\wscript.exe` as the binary executable.
- Fixed redundant 2.45 GB PyTorch wheel re-downloads on machines with pre-existing global PyTorch installations.
- Fixed single-quote string literal parsing errors inside Windows Registry association rules in Inno Setup.

---

## [v3.0.0] - 2026-05-15

### Added
- Initial desktop GUI release using PyQt5 with customizable dark/light themes.
- Support for multi-modality NIfTI volumetric rendering (`T1`, `T2`, `T1ce`, `FLAIR`).
- Basic MONAI UNet inference integration.
