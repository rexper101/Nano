@echo off
title Nano AI v5
color 0C

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║     NANO AI ASSISTANT v5                    ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: Start Ollama if not running
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %errorlevel% neq 0 (
    echo [1/3] Starting Ollama...
    start /min "Ollama" ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo [1/3] Ollama already running
)

:: Start MCP tool server
echo [2/3] Starting MCP Tool Server (port 8001)...
start /min "Nano MCP Server" python server.py

timeout /t 2 /nobreak >nul

:: Open browser
echo [3/3] Opening dashboard...
start "" http://localhost:8000

:: Start agent
echo.
echo  Dashboard : http://localhost:8000
echo  MCP Tools : http://localhost:8001
echo  Type your commands below.
echo.
python agent_nano.py --text

pause