"""
Nano MCP tool server
====================

This file exposes a set of simple Windows helper tools.
The tools are available over MCP and can be used by the Nano assistant.
"""

import asyncio
import datetime
import os
import platform
import subprocess
import sys
import webbrowser
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Install MCP first: pip install mcp[cli]")
    sys.exit(1)

mcp = FastMCP(
    name="nano",
    instructions="You are Nano, a friendly AI assistant for Windows. Always reply in English."
)


def _run_powershell(command: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


@mcp.tool()
def get_current_time() -> str:
    """Return the current date and time."""
    return datetime.datetime.now().strftime("%I:%M %p, %A %B %d %Y")


@mcp.tool()
def get_system_info() -> str:
    """Return basic system stats for CPU, memory, disk, and uptime."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = str(datetime.datetime.now() - boot).split(".")[0]
        return (
            f"OS: {platform.system()} {platform.release()}\n"
            f"CPU: {cpu}%\n"
            f"RAM: {ram.used / 1e9:.1f}GB / {ram.total / 1e9:.1f}GB ({ram.percent}%)\n"
            f"Disk: {disk.used / 1e9:.1f}GB / {disk.total / 1e9:.1f}GB\n"
            f"Uptime: {uptime}"
        )
    except ImportError:
        result = _run_powershell("systeminfo")
        lines = [line for line in result.stdout.splitlines() if any(key in line for key in ["OS", "RAM", "Memory"])]
        return "\n".join(lines[:6])


@mcp.tool()
def type_text(text: str) -> str:
    """Type the given text into the currently active window."""
    try:
        import pyautogui
        import time
        time.sleep(1)
        pyautogui.write(text, interval=0.05)
        return "Text typed successfully."
    except ImportError:
        return "pyautogui is not installed. Install it with: pip install pyautogui"
    except Exception as exc:
        return f"Could not type text: {exc}"


@mcp.tool()
def get_weather(city: str = "Pune") -> str:
    """Fetch current weather for a city without using an API key."""
    try:
        import httpx
        response = httpx.get(f"https://wttr.in/{city}?format=3", timeout=5.0)
        return response.text.strip()
    except ImportError:
        return "httpx is not installed. Install it with: pip install httpx"
    except Exception as exc:
        return f"Could not get weather: {exc}"


@mcp.tool()
def set_volume(level: int) -> str:
    """Set the system volume between 0 and 100."""
    volume_level = max(0, min(100, level))
    try:
        subprocess.run(["nircmd", "setsysvolume", str(int(volume_level * 655.35))], capture_output=True)
        return f"Volume set to {volume_level}%"
    except Exception:
        return "Unable to set volume. Install nircmd: https://www.nirsoft.net/utils/nircmd.html"


@mcp.tool()
def take_screenshot() -> str:
    """Take a screenshot and save it to the Desktop."""
    try:
        import mss
        from PIL import Image
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Desktop/screenshot_{timestamp}.png")
        with mss.mss() as sct:
            raw = sct.grab(sct.monitors[1])
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            img.save(path)
        os.startfile(os.path.dirname(path))
        return f"Screenshot saved to Desktop: {path}"
    except ImportError:
        return "Missing dependency: install mss and pillow with pip install mss pillow"
    except Exception as exc:
        return f"Could not take screenshot: {exc}"


@mcp.tool()
def get_clipboard() -> str:
    """Read the current contents of the Windows clipboard."""
    try:
        result = _run_powershell("Get-Clipboard")
        text = result.stdout.strip()
        return text or "Clipboard is empty."
    except Exception as exc:
        return f"Could not read clipboard: {exc}"


@mcp.tool()
def set_clipboard(text: str) -> str:
    """Copy text into the Windows clipboard."""
    try:
        safe_text = text.replace("'", "''")
        _run_powershell(f"Set-Clipboard -Value '{safe_text}'")
        return f"Copied to clipboard: {text[:50]}"
    except Exception as exc:
        return f"Could not set clipboard: {exc}"


@mcp.tool()
def run_command(command: str) -> str:
    """Run a PowerShell command and return the result."""
    blocked = ["format c:", "rm -rf /", "shutdown /r /t 0", "reg delete hklm\\sam"]
    if any(term in command.lower() for term in blocked):
        return f"Blocked dangerous command: {command}"
    print(f"[CMD] {command}")
    try:
        result = _run_powershell(command, timeout=60)
        output = (result.stdout or result.stderr).strip()
        if not output:
            return f"Done: {command}"
        lines = output.splitlines()
        if len(lines) > 40:
            output = "\n".join(lines[:40]) + f"\n... ({len(lines) - 40} more)"
        return output
    except subprocess.TimeoutExpired:
        return "Command timed out after 60 seconds."
    except Exception as exc:
        return f"Error: {exc}"
    """Run any Windows PowerShell command and return real output."""
    BLOCKED = ["format c:","rm -rf /","shutdown /r /t 0","reg delete hklm\\sam"]
    if any(b in command.lower() for b in BLOCKED):
        return f"Blocked: {command}"
    print(f"[CMD] {command}")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace", cwd=os.path.expanduser("~")
        )
        out = (r.stdout or r.stderr or "").strip()
        if not out: return f"Done: {command}"
        lines = out.splitlines()
        if len(lines) > 40:
            out = "\n".join(lines[:40]) + f"\n... ({len(lines)-40} more)"
        return out
    except subprocess.TimeoutExpired:
        return "Timed out after 60s."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def open_application(app_name: str) -> str:
    """Open a Windows app: chrome, vscode, notepad, spotify, calculator, etc."""
    MAP = {"chrome":"chrome","firefox":"firefox","vs code":"code","vscode":"code",
           "code":"code","notepad":"notepad","calculator":"calc","spotify":"spotify",
           "discord":"discord","explorer":"explorer","terminal":"wt","cmd":"cmd",
           "powershell":"powershell","word":"winword","excel":"excel",
           "task manager":"taskmgr","paint":"mspaint","vlc":"vlc"}
    exe = MAP.get(app_name.lower().strip(), app_name)
    try:
        subprocess.Popen(exe, shell=True)
        return f"Opened {app_name}."
    except Exception as e:
        return f"Could not open {app_name}: {e}"

@mcp.tool()
def get_battery_status() -> str:
    """Get battery percentage and charging status."""
    try:
        import psutil
        b = psutil.sensors_battery()
        if b:
            return f"Battery: {b.percent:.0f}% ({'charging' if b.power_plugged else 'on battery'})"
        return "No battery detected."
    except Exception as e:
        return f"Error: {e}"

# ── WEB ───────────────────────────────────────────────────────────────────────

@mcp.tool()
def search_web(query: str) -> str:
    """Search DuckDuckGo — no API key needed."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddg:
            results = list(ddg.text(query, max_results=4))
        if not results:
            return f"No results for: {query}"
        lines = [f"Results for: {query}\n"]
        for r in results:
            lines.append(f"• {r['title']}\n  {r['body'][:150]}\n  {r['href']}\n")
        return "\n".join(lines)
    except ImportError:
        webbrowser.open(f"https://duckduckgo.com/?q={query.replace(' ','+')}")
        return f"Opened browser search for: {query}"
    except Exception as e:
        return f"Search error: {e}"

@mcp.tool()
def get_news(topic: str = "technology") -> str:
    """Get latest news on any topic."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddg:
            results = list(ddg.news(topic, max_results=5))
        lines = [f"News: {topic}\n"]
        for r in results:
            lines.append(f"• {r['title']}\n  {r.get('body','')[:120]}\n  {r.get('source','')}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def open_url(url: str) -> str:
    """Open any URL in Chrome."""
    if not url.startswith("http"): url = "https://" + url
    webbrowser.open(url)
    return f"Opened: {url}"

@mcp.tool()
def play_on_youtube(query: str) -> str:
    """Open YouTube and search for a song or video."""
    url = f"https://www.youtube.com/results?search_query={query.replace(' ','+')}"
    webbrowser.open(url)
    return f"Searching YouTube for: {query}"

# ── FILES ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_folder(name: str, location: str = "desktop") -> str:
    """Create a folder on Desktop, Documents, or Downloads."""
    bases = {"desktop": os.path.expanduser("~/Desktop"),
             "documents": os.path.expanduser("~/Documents"),
             "downloads": os.path.expanduser("~/Downloads")}
    path = Path(bases.get(location.lower(), bases["desktop"])) / name
    path.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(f'explorer "{path}"', shell=True)
    return f"Created: {path}"

@mcp.tool()
def create_file(name: str, content: str = "", location: str = "desktop") -> str:
    """Create a file with optional content and open it."""
    bases = {"desktop": os.path.expanduser("~/Desktop"),
             "documents": os.path.expanduser("~/Documents")}
    path = Path(bases.get(location.lower(), bases["desktop"])) / name
    path.write_text(content, encoding="utf-8")
    os.startfile(str(path))
    return f"Created: {path}"

