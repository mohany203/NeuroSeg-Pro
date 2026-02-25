@echo off
setlocal
echo Setting up environment...

:: Force venv path priority to avoid Anaconda conflict
set VENV_PATH=%~dp0.venv
set PYTHONPATH=%~dp0
set PATH=%VENV_PATH%\Scripts;%VENV_PATH%\Lib\site-packages\PyQt5\Qt5\bin;%PATH%

echo Starting NeuroSeg Pro...
"%VENV_PATH%\Scripts\python.exe" app/main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application crashed with error code %ERRORLEVEL%
    pause
)
endlocal
