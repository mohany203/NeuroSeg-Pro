' NeuroSeg Pro v4.0.0 Silent Application Launcher
' Eliminates command prompt windows while properly configuring Python virtual environment paths in LocalAppData

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Determine application root directory
AppDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = AppDir

' Locate runtime environment in LocalAppData
LocalAppDataDir = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\NeuroSegPro"
VenvDir = LocalAppDataDir & "\.venv"
PythonwExe = VenvDir & "\Scripts\pythonw.exe"

' Check if runtime components exist
If Not fso.FileExists(PythonwExe) Then
    MsgText = "Runtime components have not yet been installed." & vbCrLf & vbCrLf & _
              "NeuroSeg Pro needs to finish installing Python and required clinical libraries." & vbCrLf & vbCrLf & _
              "Would you like to launch the Repair Tool now?"
    Ans = MsgBox(MsgText, vbYesNo + vbExclamation, "NeuroSeg Pro Runtime Missing")
    If Ans = vbYes Then
        RepairCmd = "powershell.exe -ExecutionPolicy Bypass -NoProfile -File """ & AppDir & "\install.ps1"" -Repair"
        WshShell.Run RepairCmd, 1, False
    End If
    WScript.Quit 0
End If

' Configure environment variables
WshShell.Environment("PROCESS")("PYTHONPATH") = AppDir
WshShell.Environment("PROCESS")("KMP_DUPLICATE_LIB_OK") = "TRUE"
WshShell.Environment("PROCESS")("TF_ENABLE_ONEDNN_OPTS") = "0"
WshShell.Environment("PROCESS")("PATH") = VenvDir & "\Scripts;" & VenvDir & "\Lib\site-packages\PyQt5\Qt5\bin;" & WshShell.Environment("PROCESS")("PATH")

' Check if arguments were passed (e.g., file association launch)
ArgsStr = ""
If WScript.Arguments.Count > 0 Then
    For i = 0 To WScript.Arguments.Count - 1
        ArgsStr = ArgsStr & " """ & WScript.Arguments(i) & """"
    Next
End If

' Launch pythonw executable silently (window style 0 = hidden console)
MainScript = """" & AppDir & "\app\main.py"""
WshShell.Run """" & PythonwExe & """ " & MainScript & ArgsStr, 0, False
