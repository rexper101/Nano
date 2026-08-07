"""
App Tool — Fixed for Windows
==============================
Opens and closes applications using os.startfile and subprocess.
"""

import os
import re
import subprocess


APP_MAP = {
    "chrome":       ["chrome", "google chrome"],
    "firefox":      ["firefox"],
    "edge":         ["msedge"],
    "vs code":      ["code"],
    "vscode":       ["code"],
    "code":         ["code"],
    "notepad":      ["notepad"],
    "calculator":   ["calc"],
    "spotify":      ["spotify"],
    "discord":      ["discord"],
    "whatsapp":     ["WhatsApp"],
    "explorer":     ["explorer"],
    "file explorer":["explorer"],
    "terminal":     ["wt", "cmd"],
    "cmd":          ["cmd"],
    "powershell":   ["powershell"],
    "word":         ["winword"],
    "excel":        ["excel"],
    "powerpoint":   ["powerpnt"],
    "task manager": ["taskmgr"],
    "paint":        ["mspaint"],
    "vlc":          ["vlc"],
    "zoom":         ["zoom"],
    "teams":        ["teams"],
    "obs":          ["obs64"],
    "steam":        ["steam"],
    "brave":        ["brave"],
    "opera":        ["opera"],
    "notion":       ["notion"],
    "slack":        ["slack"],
}

PROCESS_MAP = {
    "chrome": "chrome.exe", "firefox": "firefox.exe",
    "edge": "msedge.exe", "vs code": "Code.exe", "vscode": "Code.exe",
    "notepad": "notepad.exe", "spotify": "Spotify.exe",
    "discord": "Discord.exe", "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE", "powershell": "powershell.exe",
    "vlc": "vlc.exe", "zoom": "Zoom.exe",
}

