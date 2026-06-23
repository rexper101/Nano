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


class AppTool:
    def run(self, user_text: str) -> str:
        t = user_text.lower()
        if any(w in t for w in ["close","kill","quit","exit","stop"]):
            return self._close(t)
        return self._open(t, user_text)

    def _find_key(self, text: str):
        # Longest match first
        for key in sorted(APP_MAP.keys(), key=len, reverse=True):
            if key in text:
                return key
        return None

    def _open(self, text_lower: str, original: str) -> str:
        key = self._find_key(text_lower)

        if key:
            exes = APP_MAP[key]
            for exe in exes:
                try:
                    subprocess.Popen(exe, shell=True,
                                     creationflags=subprocess.CREATE_NO_WINDOW
                                     if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    return f"Opened {key.title()}."
                except Exception:
                    continue
            return f"Could not open {key}. Make sure it is installed."

        # Try to extract any word after open/launch/start
        m = re.search(r"(?:open|launch|start)\s+([\w\s]+?)(?:\s+please|$)", text_lower)
        if m:
            app = m.group(1).strip()
            try:
                subprocess.Popen(app, shell=True)
                return f"Opened {app}."
            except Exception:
                # Try os.startfile for file paths
                try:
                    os.startfile(app)
                    return f"Opened {app}."
                except Exception as e:
                    return f"Could not open {app}: {e}"

        return ""

    def _close(self, text: str) -> str:
        key = self._find_key(text)
        if not key:
            return ""
        proc = PROCESS_MAP.get(key, f"{key}.exe")
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/IM", proc],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return f"Closed {key.title()}."
            return f"Could not close {key}: not running."
        except Exception as e:
            return f"Error: {e}"