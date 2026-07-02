; Inno Setup Script for NeuroSeg Pro v4.0.0
; Refactored Commercial-Grade Volumetric Clinical Segmentation Platform Installer

#define MyAppName "NeuroSeg-Pro"
#define MyAppVersion "4.0.0"
#define MyAppPublisher "NeuroSeg Clinical AI Team"
#define MyAppURL "https://github.com/mohany203/NeuroSeg-Pro"
#define MyAppExeName "NeuroSegPro.vbs"
#define WScriptExe "{sys}\wscript.exe"

[Setup]
; Unique GUID identifying NeuroSeg-Pro applications across upgrades
AppId={{D1A3B0F1-5E24-4B7C-A8E2-9E5C8D4B2A10}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Version Info and Architecture Specifications for Commercial Windows Deployment
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription="NeuroSeg Pro Volumetric Segmentation Platform"
VersionInfoProductVersion={#MyAppVersion}
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes

; Request Administrator privileges via standard Windows UAC prompt
PrivilegesRequired=admin
OutputDir=dist
OutputBaseFilename=NeuroSegPro_Setup_v4.0.0
SetupIconFile=assets\NeuroSeg_App_Icon.ico
UninstallDisplayIcon={app}\assets\NeuroSeg_App_Icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Package clean production runtime artifacts staged in release/. Avoids distributing repository dev files.
Source: "release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc,*.log"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{#WScriptExe}"; Parameters: """{app}\{#MyAppExeName}"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\NeuroSeg_App_Icon.ico"
Name: "{group}\Repair & Maintenance Tool"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\install.ps1"" -Repair"; WorkingDir: "{app}"; IconFilename: "{app}\assets\NeuroSeg_App_Icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{#WScriptExe}"; Parameters: """{app}\{#MyAppExeName}"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\NeuroSeg_App_Icon.ico"; Tasks: desktopicon

[Run]
; Allow immediate launch upon setup completion via wscript launcher (only if bootstrapper succeeded)
Filename: "{#WScriptExe}"; Parameters: """{app}\{#MyAppExeName}"""; Description: "Launch NeuroSeg Pro v{#MyAppVersion}"; Flags: postinstall nowait skipifsilent unchecked; Check: CanLaunchApp

[Registry]
; Register .nii and .nii.gz file associations directly with silent VBS launcher
Root: HKCU; Subkey: "Software\Classes\.nii"; ValueType: string; ValueName: ""; ValueData: "NeuroSegPro.StudyFile"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.nii.gz"; ValueType: string; ValueName: ""; ValueData: "NeuroSegPro.StudyFile"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\NeuroSegPro.StudyFile"; ValueType: string; ValueName: ""; ValueData: "NeuroSeg Pro Volumetric Study"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\NeuroSegPro.StudyFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\assets\NeuroSeg_App_Icon.ico,0"
Root: HKCU; Subkey: "Software\Classes\NeuroSegPro.StudyFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{#WScriptExe}"" ""{app}\{#MyAppExeName}"" ""%1"""

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\NeuroSegPro\.venv"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
var
  BootstrapperFailed: Boolean;

function CanLaunchApp: Boolean;
begin
  Result := not BootstrapperFailed;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  LogDir: string;
begin
  if CurStep = ssPostInstall then
  begin
    BootstrapperFailed := False;
    WizardForm.StatusLabel.Caption := 'Orchestrating Python runtime and clinical AI dependencies...';
    if Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
            '-ExecutionPolicy Bypass -NoProfile -File "' + ExpandConstant('{app}\install.ps1') + '" -Unattended',
            ExpandConstant('{app}'), SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode <> 0 then
      begin
        BootstrapperFailed := True;
        LogDir := ExpandConstant('{localappdata}\NeuroSegPro\logs');
        MsgBox('NeuroSeg Pro runtime setup completed with exit code ' + IntToStr(ResultCode) + '.' + #13#10 + #13#10 +
               'Installation was incomplete. Please review diagnostic logs at:' + #13#10 + LogDir + #13#10 + #13#10 +
               'You can run the "Repair & Maintenance Tool" from the Start Menu once network or system requirements are met.', mbError, MB_OK);
      end;
    end
    else
    begin
      BootstrapperFailed := True;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataDir: string;
  LocalAppDataDir: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    LocalAppDataDir := ExpandConstant('{localappdata}\NeuroSegPro');
    if DirExists(LocalAppDataDir) then
    begin
      DelTree(LocalAppDataDir, True, True, True);
    end;

    AppDataDir := ExpandConstant('{userappdata}\NeuroSegPro');
    if DirExists(AppDataDir) then
    begin
      if MsgBox('Do you want to completely remove saved patient studies, cached segmentation models, and clinical preferences (' + AppDataDir + ')?', mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(AppDataDir, True, True, True);
      end;
    end;
  end;
end;
