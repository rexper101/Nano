"""
CMD Tool
=========
Runs shell commands via PowerShell on Windows.
Has a safety blocklist — dangerous commands are refused.

Examples Nano can handle:
  "run ipconfig"
  "install requests using pip"
  "check disk space"
  "run my script train.py"
  "git status"
  "create a folder called MyProject"
"""

import subprocess
import re
import os


# Commands that are always blocked
BLOCKED = [
    "format", "del /f", "rm -rf", "shutdown", "taskkill",
    "reg delete", "diskpart", "cipher /w", "sfc /scannow",
    "net user", "net localgroup",
]


class CMDTool:
    def run(self, user_text: str) -> str:
        command = self._extract_command(user_text)
        if not command:
            return ""

        # Safety check
        for blocked in BLOCKED:
            if blocked in command.lower():
                return f"Blocked: '{blocked}' is not allowed for safety."

        return self._execute(command)

    def _extract_command(self, text: str) -> str:
        """Pull the actual command from natural language."""
        text = text.strip()

        # Direct patterns
        patterns = [
            r"run\s+(.+)",
            r"execute\s+(.+)",
            r"terminal[:\s]+(.+)",
            r"command[:\s]+(.+)",
            r"shell[:\s]+(.+)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()

        # Natural language → command mapping
        mappings = {
            "install (.+) using pip":  lambda m: f"pip install {m.group(1)}",
            "install (.+)":            lambda m: f"pip install {m.group(1)}",
            "check disk space":        lambda _: "wmic logicaldisk get size,freespace,caption",
            "disk space":              lambda _: "wmic logicaldisk get size,freespace,caption",
            "list files":              lambda _: "dir",
            "show ip":                 lambda _: "ipconfig",
            "ipconfig":                lambda _: "ipconfig",
            "git status":              lambda _: "git status",
            "git log":                 lambda _: "git log --oneline -10",
            "python version":          lambda _: "python --version",
            "pip list":                lambda _: "pip list",
            "running processes":       lambda _: "tasklist",
            r"run (.+\.py)":           lambda m: f"python {m.group(1)}",
            r"ping (.+)":              lambda m: f"ping -n 4 {m.group(1)}",
        }
        for pattern, builder in mappings.items():
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return builder(m)

        return ""

    def _execute(self, command: str) -> str:
        print(f"\033[35m[CMD] Running: {command}\033[0m")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.expanduser("~"),
            )
            output = (result.stdout or result.stderr or "").strip()
            # Truncate long output
            if len(output) > 800:
                output = output[:800] + "\n...(truncated)"
            return output if output else "Command executed successfully."
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds."
        except Exception as e:
            return f"Error: {e}"
