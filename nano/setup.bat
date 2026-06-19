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

:: Check Ollama
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [WARNING] Ollama not found.
    echo  Download from: https://ollama.ai
    echo  After installing, run this setup again.
    pause
    exit /b 1
)
echo  [OK] Ollama found

:: Upgrade pip
echo.
echo  [1/5] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Install packages
echo  [2/5] Installing Python packages...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  [RETRY] Trying with --prefer-binary...
    pip install -r requirements.txt --prefer-binary --quiet
)

:: Install webrtcvad (Windows wheel)
echo  [3/5] Installing Windows audio packages...
pip install webrtcvad-wheels --quiet
pip install pyaudio --quiet
if %errorlevel% neq 0 (
    pip install pipwin --quiet
    pipwin install pyaudio
)

:: Install Playwright browser
echo  [4/5] Installing Playwright Chromium...
playwright install chromium --quiet

:: Pull Ollama models
echo  [5/5] Pulling AI models (this takes a while — ~7GB total)...
echo.
echo  Pulling qwen2.5:7b (main brain — 4.7GB)...
ollama pull qwen2.5:7b

echo  Pulling phi3:mini (fast routing — 2.3GB)...
ollama pull phi3:mini

echo  Pulling llava:7b (screen vision — 4.7GB)...
ollama pull llava:7b

:: Create directories
echo.
echo  Creating folders...
mkdir data\screenshots 2>nul
mkdir data\memory 2>nul
mkdir data\recordings 2>nul
mkdir Documents\Nano_CV 2>nul

:: Done
echo.
echo  ████████████████████████████████████████████
echo   Setup Complete!
echo  ████████████████████████████████████████████
echo.
echo  To start Nano:
echo.
echo    1. Open a terminal and run:  ollama serve
echo    2. Open another terminal:    python main.py --text
echo    3. Or double-click:          run_nano.bat
echo.
pause
