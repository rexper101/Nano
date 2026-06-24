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

