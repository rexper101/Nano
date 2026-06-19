"""
App Tool
=========
Open and close applications by name on Windows.

Examples:
  "open Chrome"
  "launch VS Code"
  "open Spotify"
  "close Notepad"
  "open calculator"
"""

import subprocess
import re
import os


# App name → Windows executable / path
APP_MAP = {
    "chrome":      ["chrome", "google chrome",
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
    "firefox":     ["firefox"],
    "edge":        ["msedge"],
    "vs code":     ["code"],
    "vscode":      ["code"],
    "notepad":     ["notepad"],
    "calculator":  ["calc"],
    "spotify":     ["spotify",
                    rf"{os.path.expanduser('~')}\AppData\Roaming\Spotify\Spotify.exe"],
    "discord":     ["discord",
                    rf"{os.path.expanduser('~')}\AppData\Local\Discord\Update.exe --processStart Discord.exe"],
    "whatsapp":    ["whatsapp"],
    "file explorer":["explorer"],
    "explorer":    ["explorer"],
    "terminal":    ["wt", "cmd"],
    "powershell":  ["powershell"],
    "word":        ["winword", r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],
    "excel":       ["excel",  r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"],
    "powerpoint":  ["powerpnt"],
    "task manager":["taskmgr"],
    "paint":       ["mspaint"],
    "vlc":         ["vlc", r"C:\Program Files\VideoLAN\VLC\vlc.exe"],
    "zoom":        ["zoom"],
    "teams":       ["teams"],
    "obs":         ["obs64", "obs"],
}


class AppTool:
    def run(self, user_text: str) -> str:
        text = user_text.lower()

        # Close command
        if any(w in text for w in ["close", "kill", "quit", "exit"]):
            return self._close_app(text)

        # Open command
        return self._open_app(text)

    def _find_app_key(self, text: str) -> str | None:
        """Find which app the user mentioned."""
        for key in APP_MAP:
            if key in text:
                return key
        return None

    def _open_app(self, text: str) -> str:
        key = self._find_app_key(text)
        if not key:
            # Try to extract any word after "open" or "launch"
            m = re.search(r"(?:open|launch|start)\s+(\w[\w\s]*)", text)
            if m:
                app_name = m.group(1).strip()
                try:
                    subprocess.Popen(app_name, shell=True)
                    return f"Opened {app_name}."
                except Exception as e:
                    return f"Could not open {app_name}: {e}"
            return ""

        for exe in APP_MAP[key]:
            try:
                subprocess.Popen(exe, shell=True)
                return f"Opened {key.title()}."
            except Exception:
                continue

        return f"Could not open {key}. Make sure it is installed."

    def _close_app(self, text: str) -> str:
        key = self._find_app_key(text)
        if not key:
            return ""

        # Map app name to process name for taskkill
        process_map = {
            "chrome":      "chrome.exe",
            "firefox":     "firefox.exe",
            "edge":        "msedge.exe",
            "vs code":     "Code.exe",
            "vscode":      "Code.exe",
            "notepad":     "notepad.exe",
            "calculator":  "CalculatorApp.exe",
            "spotify":     "Spotify.exe",
            "discord":     "Discord.exe",
            "word":        "WINWORD.EXE",
            "excel":       "EXCEL.EXE",
            "powershell":  "powershell.exe",
        }
        proc = process_map.get(key, f"{key}.exe")
        result = subprocess.run(
            ["taskkill", "/F", "/IM", proc],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Closed {key.title()}."
        return f"Could not close {key}: process not found."
