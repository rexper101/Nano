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

        # system info
        if any(w in tl for w in ["ipconfig","my ip","ip address","network"]):
            return "ipconfig"
        if any(w in tl for w in ["disk space","disk usage","storage","free space"]):
            return "wmic logicaldisk get caption,size,freespace /format:list"
        if any(w in tl for w in ["cpu","processor"]):
            return "wmic cpu get name,loadpercentage"
        if any(w in tl for w in ["ram","memory usage"]):
            return "wmic OS get freephysicalmemory,totalvisiblememorysize"
        if any(w in tl for w in ["running processes","task list","process list"]):
            return "tasklist"
        if any(w in tl for w in ["python version","which python"]):
            return f'"{sys.executable}" --version'
        if any(w in tl for w in ["pip list","installed packages"]):
            return "pip list"
        if "whoami" in tl:
            return "whoami"
        if "hostname" in tl:
            return "hostname"
        if any(w in tl for w in ["system info","os version","windows version"]):
            return 'systeminfo | findstr /C:"OS Name" /C:"OS Version" /C:"Total Physical"'
        if any(w in tl for w in ["list files","show files","dir","ls"]):
            return "dir"
        if any(w in tl for w in ["environment","env vars"]):
            return "set"

        # mkdir
        m = re.search(r"(?:create|make|mkdir)\s+(?:a\s+)?(?:folder|directory)\s+(?:called|named)?\s*[\"']?([^\"']+?)[\"']?\s*(?:on|in|at|$)", tl)
        if m:
            name = m.group(1).strip()
            base = "Desktop"
            if "documents" in tl: base = "Documents"
            elif "downloads" in tl: base = "Downloads"
            path = os.path.join(os.path.expanduser(f"~/{base}"), name)
            return f'mkdir "{path}"'

        # ping
        m = re.search(r"ping\s+([\w\.\-]+)", tl)
        if m:
            return f"ping -n 4 {m.group(1)}"

        # run python script
        m = re.search(r"run\s+([\w\-\.]+\.py)", tl)
        if m:
            return f'"{sys.executable}" {m.group(1)}'

        # npm
        m = re.search(r"npm\s+(install|start|run|build|test)\s*(.*)", tl)
        if m:
            return f"npm {m.group(1)} {m.group(2)}".strip()

        # taskkill
        m = re.search(r"(?:kill|stop|end)\s+(?:process\s+)?[\"']?([^\"']+)[\"']?$", tl)
        if m:
            name = m.group(1).strip()
            if not name.endswith(".exe"): name += ".exe"
            return f'taskkill /F /IM "{name}"'

        return ""

    def _execute(self, command: str) -> str:
        cmd_lower = command.lower().strip()
        for blocked in HARD_BLOCKED:
            if blocked in cmd_lower:
                return f"Blocked for safety: '{blocked}'"

        print(f"[CMD] Running: {command}")

        try:
            if os.name == "nt":
                full_cmd = ["powershell", "-NoProfile", "-Command", command]
            else:
                full_cmd = ["/bin/bash", "-c", command]

            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.path.expanduser("~"),
                encoding="utf-8",
                errors="replace",
            )

            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()

            output = stdout
            if stderr and not stdout:
                output = stderr
            elif stderr and "error" in stderr.lower():
                output = stdout + "\n" + stderr

            if not output:
                return f"Done: {command}"

            lines = output.splitlines()
            if len(lines) > 50:
                output = "\n".join(lines[:50]) + f"\n... ({len(lines)-50} more lines)"

            return output

        except subprocess.TimeoutExpired:
            return "Command timed out after 60 seconds."
        except Exception as e:
            return f"Error: {e}"