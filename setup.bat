@echo off
title Nano AI Desktop Assistant — Setup
color 0B

echo.
echo  ████████████████████████████████████████████
echo   Nano AI Desktop Assistant — Windows Setup
echo  ████████████████████████████████████████████
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found!
    echo  Download from: https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo  [OK] Python found

