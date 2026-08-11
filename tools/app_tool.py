"""
App Tool — Fixed for Windows
==============================
Opens and closes applications using subprocess and os.startfile.
Provides better alias handling, safer fallback behavior, and clearer messages.
"""

import os
import re
import shutil
import subprocess


APP_CONFIG = {
    "chrome": {
        "aliases": ["google chrome"],
        "launch": ["chrome"],
        "process": "chrome.exe",
    },
    "firefox": {
        "aliases": [],
        "launch": ["firefox"],
        "process": "firefox.exe",
    },
    "edge": {
        "aliases": ["microsoft edge"],
        "launch": ["msedge"],
        "process": "msedge.exe",
    },
    "code": {
        "aliases": ["vs code", "vscode"],
        "launch": ["code"],
        "process": "Code.exe",
    },
    "notepad": {
        "aliases": [],
        "launch": ["notepad"],
        "process": "notepad.exe",
    },
    "calculator": {
        "aliases": ["calc"],
        "launch": ["calc"],
        "process": "Calculator.exe",
    },
    "spotify": {
        "aliases": [],
        "launch": ["spotify"],
        "process": "Spotify.exe",
    },
    "discord": {
        "aliases": [],
        "launch": ["discord"],
        "process": "Discord.exe",
    },
    "whatsapp": {
        "aliases": [],
        "launch": ["WhatsApp"],
        "process": "WhatsApp.exe",
    },
    "explorer": {
        "aliases": ["file explorer", "window explorer"],
        "launch": ["explorer"],
        "process": "explorer.exe",
    },
    "terminal": {
        "aliases": ["command prompt", "cmd prompt"],
        "launch": ["wt", "cmd"],
        "process": "WindowsTerminal.exe",
    },
    "cmd": {
        "aliases": ["command prompt"],
        "launch": ["cmd"],
        "process": "cmd.exe",
    },
    "powershell": {
        "aliases": [],
        "launch": ["powershell"],
        "process": "powershell.exe",
    },
    "word": {
        "aliases": ["microsoft word"],
        "launch": ["winword"],
        "process": "WINWORD.EXE",
    },
    "excel": {
        "aliases": ["microsoft excel"],
        "launch": ["excel"],
        "process": "EXCEL.EXE",
    },
    "powerpoint": {
        "aliases": ["microsoft powerpoint"],
        "launch": ["powerpnt"],
        "process": "POWERPNT.EXE",
    },
    "task manager": {
        "aliases": [],
        "launch": ["taskmgr"],
        "process": "Taskmgr.exe",
    },
    "paint": {
        "aliases": ["mspaint"],
        "launch": ["mspaint"],
        "process": "mspaint.exe",
    },
    "vlc": {
        "aliases": [],
        "launch": ["vlc"],
        "process": "vlc.exe",
    },
    "zoom": {
        "aliases": [],
        "launch": ["zoom"],
        "process": "Zoom.exe",
    },
    "teams": {
        "aliases": ["microsoft teams"],
        "launch": ["teams"],
        "process": "Teams.exe",
    },
    "obs": {
        "aliases": ["obs studio"],
        "launch": ["obs64"],
        "process": "obs64.exe",
    },
    "steam": {
        "aliases": [],
        "launch": ["steam"],
        "process": "steam.exe",
    },
    "brave": {
        "aliases": [],
        "launch": ["brave"],
        "process": "brave.exe",
    },
    "opera": {
        "aliases": [],
        "launch": ["opera"],
        "process": "opera.exe",
    },
    "notion": {
        "aliases": [],
        "launch": ["notion"],
        "process": "Notion.exe",
    },
    "slack": {
        "aliases": [],
        "launch": ["slack"],
        "process": "slack.exe",
    },
}

APP_ALIASES = {
    alias: canonical
    for canonical, spec in APP_CONFIG.items()
    for alias in [canonical] + spec["aliases"]
}

LAUNCH_COMMANDS = {
    canonical: spec["launch"]
    for canonical, spec in APP_CONFIG.items()
}

PROCESS_MAP = {
    canonical: spec["process"]
    for canonical, spec in APP_CONFIG.items()
}

CLOSE_KEYWORDS = ["close", "kill", "quit", "exit", "stop"]
OPEN_KEYWORDS = ["open", "launch", "start"]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _match_app_key(text: str) -> str | None:
    for alias in sorted(APP_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return APP_ALIASES[alias]
    return None


class AppTool:
    def run(self, user_text: str) -> str:
        text = _normalize_text(user_text)
        if any(keyword in text for keyword in CLOSE_KEYWORDS):
            return self._close(text)
        if any(keyword in text for keyword in OPEN_KEYWORDS):
            return self._open(text)
        return "I can open or close applications if you ask me to."

    def _open(self, text: str) -> str:
        key = _match_app_key(text)
        if key:
            return self._launch_app(key)

        app_name = self._extract_target(text, OPEN_KEYWORDS)
        if app_name:
            return self._launch_target(app_name)

        return "Please tell me which application to open."

    def _close(self, text: str) -> str:
        key = _match_app_key(text)
        if key:
            process = PROCESS_MAP.get(key)
            if not process:
                return f"I know how to start {key}, but I cannot automatically close it."
            return self._kill_process(process, key)

        app_name = self._extract_target(text, CLOSE_KEYWORDS)
        if app_name:
            key = _match_app_key(app_name)
            if key:
                process = PROCESS_MAP.get(key)
                if process:
                    return self._kill_process(process, key)
            return f"I could not determine a supported process for {app_name}."

        return "Please tell me which application to close."

    def _launch_app(self, key: str) -> str:
        commands = LAUNCH_COMMANDS.get(key, [])
        for command in commands:
            if self._try_launch(command):
                return f"Opened {key.title()}."
        return f"Could not open {key}. Make sure it is installed."

    def _launch_target(self, target: str) -> str:
        if os.path.exists(target):
            try:
                os.startfile(target)
                return f"Opened {target}."
            except OSError as exc:
                return f"Could not open {target}: {exc}"

        if shutil.which(target):
            if self._try_launch(target, use_shell=False):
                return f"Opened {target}."

        if self._try_launch(target):
            return f"Opened {target}."

        return f"Could not open {target}."

    def _try_launch(self, command: str, use_shell: bool = True) -> bool:
        try:
            if use_shell:
                subprocess.Popen(
                    command,
                    shell=True,
                    creationflags=(subprocess.CREATE_NO_WINDOW
                                   if hasattr(subprocess, "CREATE_NO_WINDOW") else 0),
                )
            else:
                subprocess.Popen([command], creationflags=(subprocess.CREATE_NO_WINDOW
                                                          if hasattr(subprocess, "CREATE_NO_WINDOW") else 0))
            return True
        except OSError:
            return False
        except Exception:
            return False

    def _kill_process(self, process: str, name: str) -> str:
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", process],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Closed {name.title()}."
        except subprocess.CalledProcessError:
            return f"Could not close {name}. It may not be running."

    def _extract_target(self, text: str, keywords: list[str]) -> str | None:
        pattern = rf"(?:{''.join(re.escape(word) + r'\s+' for word in keywords)})" \
                  r"([\w\s\.\\:]+?)" \
                  r"(?:\s+please|\s+now|$)"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None

