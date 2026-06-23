"""
CMD Tool — Fixed
=================
Actually runs commands on Windows via subprocess.
Minimal safety list — only blocks truly dangerous ops.
"""

import os
import re
import subprocess


# Only block genuinely destructive commands
BLOCKED = [
    "format c:", "rm -rf /", "del /f /s /q c:\\",
    "shutdown /r", "shutdown /s",
    "reg delete hklm", "reg delete hkcu",
    "net user administrator",
]


class CMDTool:
    def run(self, user_text: str) -> str:
        cmd = self._extract(user_text)
        if not cmd:
            return ""

        # Safety check
        cmd_lower = cmd.lower()
        for b in BLOCKED:
            if b in cmd_lower:
                return f"Blocked for safety: {b}"

        return self._execute(cmd)

    def _extract(self, text: str) -> str:
        """Convert natural language to a real command."""
        t = text.strip()

        # ── Direct "run X" / "execute X" ──────────────────────────────────
        for pat in [
            r"(?:run|execute|terminal|command|cmd)[:\s]+(.+)",
            r"(?:open|launch)\s+(?:a\s+)?(?:new\s+)?(?:cmd|terminal|command prompt)",
        ]:
            m = re.search(pat, t, re.IGNORECASE)
            if m and m.lastindex:
                return m.group(1).strip()

        # ── Natural language → command ──────────────────────────────────────
        tl = t.lower()

        # pip installs
        m = re.search(r"install\s+([\w\-\[\]]+(?:\s+[\w\-\[\]]+)*)\s+(?:using|with|via)?\s*pip", tl)
        if m:
            pkg = m.group(1).strip()
            return f"pip install {pkg}"

        m = re.search(r"pip\s+install\s+([\w\-\[\]]+)", tl)
        if m:
            return f"pip install {m.group(1)}"

        # git commands
        for kw in ["git status","git log","git pull","git push","git diff","git branch","git add","git commit"]:
            if kw in tl:
                return kw + (" --oneline -10" if kw == "git log" else "")

        # system info
        if any(w in tl for w in ["ipconfig","ip config","my ip","network info"]):
            return "ipconfig"
        if any(w in tl for w in ["disk space","disk usage","storage","how much space"]):
            return "wmic logicaldisk get caption,size,freespace"
        if any(w in tl for w in ["running processes","task list","what's running","processes"]):
            return "tasklist"
        if any(w in tl for w in ["python version","which python"]):
            return "python --version"
        if any(w in tl for w in ["pip list","installed packages","list packages"]):
            return "pip list"
        if "dir" in tl or "list files" in tl or "ls" in tl:
            return "dir"
        if "whoami" in tl:
            return "whoami"
        if "hostname" in tl:
            return "hostname"

        # ping
        m = re.search(r"ping\s+([\w\.\-]+)", tl)
        if m:
            return f"ping -n 4 {m.group(1)}"

        # run a python script
        m = re.search(r"run\s+([\w\-]+\.py)", tl)
        if m:
            return f"python {m.group(1)}"

        # mkdir
        m = re.search(r"(?:make|create|mkdir)\s+(?:a\s+)?(?:folder|directory)\s+(?:called|named)?\s*([\w\-\s]+)", tl)
        if m:
            name = m.group(1).strip().replace(" ","_")
            return f'mkdir "{name}"'

        return ""

    def _execute(self, command: str) -> str:
        print(f"[CMD] Executing: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.expanduser("~"),
                encoding="utf-8",
                errors="replace",
            )
            output = (result.stdout or "") + (result.stderr or "")
            output = output.strip()

            if not output:
                return f"Command completed: {command}"

            # Trim very long output
            if len(output) > 1000:
                lines  = output.splitlines()
                output = "\n".join(lines[:30])
                output += f"\n... ({len(lines)} lines total, showing first 30)"

            return output

        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds."
        except Exception as e:
            return f"Error running command: {e}"