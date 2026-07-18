@echo off
title Nano AI v5 - Voice Mode
color 0C

echo  Starting Nano in VOICE MODE...

tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %errorlevel% neq 0 (
    start /min "Ollama" ollama serve
    timeout /t 3 /nobreak >nul
)

