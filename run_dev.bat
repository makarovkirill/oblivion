@echo off
cd /d "%~dp0"
title OBLIVION - Development Console

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Running install.bat or setup.ps1 first is recommended.
    echo Attempting to launch with system Python...
    python -m oblivion.main
    pause
    exit /b 1
)

echo Starting OBLIVION service on http://127.0.0.1:8765...
".venv\Scripts\python.exe" -m oblivion.main
pause
