@echo off
title Nano AI Assistant v3 — Text Mode
color 0B

echo  Starting Nano in TEXT MODE (no microphone)...
echo.

tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %errorlevel% neq 0 (
    start /min "Ollama" ollama serve
    timeout /t 3 /nobreak >nul
)

start /min "Nano API" python api_server.py
timeout /t 2 /nobreak >nul
start "" "ui\index.html"

python main.py --text
pause
