@echo off
setlocal
set LOG_FILE=%TEMP%\NeuroSegPro_run_log.txt
echo Setting up environment... > "%LOG_FILE%" 2>&1

:: Force venv path priority to avoid Anaconda conflict
set VENV_PATH=%~dp0.venv
set PYTHONPATH=%~dp0
set PATH=%VENV_PATH%\Scripts;%VENV_PATH%\Lib\site-packages\PyQt5\Qt5\bin;%PATH%

echo Starting NeuroSeg Pro... >> "%LOG_FILE%" 2>&1
cd /d "%~dp0"
"%VENV_PATH%\Scripts\python.exe" app/main.py >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo. >> "%LOG_FILE%"
    echo Application crashed with error code %ERRORLEVEL% >> "%LOG_FILE%"
    mshta vbscript:Execute("msgbox ""NeuroSeg-Pro failed to start! Please check %LOG_FILE% for details."",48,""Launch Error"":close")
)
endlocal
