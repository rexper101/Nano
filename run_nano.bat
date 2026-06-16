@echo off
title Nano AI Assistant v3
color 0B

echo.
echo  Starting Nano AI Assistant v3...
echo  Anime avatar + Japanese voice + Chat UI
echo.

:: Start Ollama if not running
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %errorlevel% neq 0 (
    echo  [1/3] Starting Ollama...
    start /min "Ollama" ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo  [1/3] Ollama already running
)

:: Start API server in background
echo  [2/3] Starting Nano API server...
start /min "Nano API" python api_server.py

timeout /t 2 /nobreak >nul

:: Open the dashboard in browser
echo  [3/3] Opening dashboard in browser...
start "" "ui\index.html"

:: Start Nano main (voice + avatar)
echo.
echo  Starting Nano (voice mode)...
echo  Say "Hey Nano" or type below.
echo  Dashboard: ui/index.html
echo.
python main.py

pause
