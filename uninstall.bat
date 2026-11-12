@echo off
setlocal EnableDelayedExpansion

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
title OBLIVION Uninstaller

echo ============================================================
echo                  OBLIVION UNINSTALLATION
echo ============================================================
set /p USER_PIN="Enter Uninstall Key / Vvedite klyuch udaleniya: "

echo Verifying authorization key...
if exist "dist\oblivion.exe" (
    "dist\oblivion.exe" --uninstall %USER_PIN%
    goto END
)

if exist "oblivion.exe" (
    "oblivion.exe" --uninstall %USER_PIN%
    goto END
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" oblivion\main.py --uninstall %USER_PIN%
    goto END
)

python oblivion\main.py --uninstall %USER_PIN%

:END
pause
