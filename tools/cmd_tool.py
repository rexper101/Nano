"""
CMD Tool — Real-time Windows Execution
========================================
Executes commands directly on Windows via PowerShell.
Streams output in real time. Minimal safety list.
"""

import os
import re
import subprocess
import sys

HARD_BLOCKED = [
    "format c:", "del /f /s /q c:\\windows",
    "rm -rf /", "shutdown /r /t 0", "shutdown /s /t 0",
    "reg delete hklm\\sam",
]


class CMDTool:

    def run(self, user_text: str) -> str:
        cmd = self._to_command(user_text)
        if not cmd:
            return ""
        return self._execute(cmd)

    def _to_command(self, text: str) -> str:
        t  = text.strip()
        tl = t.lower()

        # Raw command after "run" / "execute"
        m = re.match(r"^(?:run|execute|cmd|terminal)[:\s]+(.+)", t, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # pip install
        m = re.search(r"install\s+([\w\-\[\],\s]+?)\s+(?:using|with|via)?\s*pip", tl)
        if m:
            return f"pip install {m.group(1).strip()}"
        m = re.search(r"pip\s+install\s+([\w\-\[\]\s,]+)", tl)
        if m:
            return f"pip install {m.group(1).strip()}"

        # pip uninstall
        m = re.search(r"(?:uninstall|remove)\s+([\w\-]+)\s+(?:using|from)?\s*pip", tl)
        if m:
            return f"pip uninstall {m.group(1)} -y"

        # git
        GIT = {"git status":"git status","git log":"git log --oneline -15",
               "git pull":"git pull","git push":"git push","git diff":"git diff",
               "git branch":"git branch -a","git fetch":"git fetch"}
        for kw, cmd in GIT.items():
            if kw in tl:
                return cmd
        m = re.search(r"git\s+(add|commit|checkout|merge|clone|init)\s*(.*)", tl)
        if m:
            return f"git {m.group(1)} {m.group(2)}".strip()

        