@echo off
setlocal EnableDelayedExpansion

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
title OBLIVION Setup

echo =====================================================================
echo   OBLIVION — Dead Man's Switch ^& Secure Eraser
echo =====================================================================
echo.

if exist "dist\OblivionSetup.exe" (
    echo Launching native GUI installer...
    start "" "dist\OblivionSetup.exe"
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation failed. Review messages above.
    pause
    exit /b %errorlevel%
)

echo.
echo [OK] Installation and service deployment complete.
echo Browser opened to: http://127.0.0.1:8765
timeout /t 5 >nul
exit /b 0
