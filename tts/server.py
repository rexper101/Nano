"""
Nano MCP Tool Server  —  server.py
=====================================
Add this file to your nano folder.
Run:  python server.py

Exposes tools via MCP on port 8001.
agent_nano.py calls these tools automatically.

Install MCP first:  pip install mcp[cli]
"""

import asyncio, datetime, os, platform, re, subprocess, sys, webbrowser
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Install MCP first:  pip install mcp[cli]")
    exit(1)

mcp = FastMCP(
    name="nano",
    instructions="You are Nano, a powerful AI desktop assistant for Windows. Always reply in English."
)

# ── SYSTEM ────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.datetime.now().strftime("%I:%M %p, %A %B %d %Y")

@mcp.tool()
def get_system_info() -> str:
    """Get CPU, RAM, disk, and OS info."""
    try:
        import psutil
        cpu  = psutil.cpu_percent(interval=0.5)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        up   = str(datetime.datetime.now() - boot).split(".")[0]
        return (f"OS: {platform.system()} {platform.release()}\n"
                f"CPU: {cpu}%\n"
                f"RAM: {ram.used/1e9:.1f}GB / {ram.total/1e9:.1f}GB ({ram.percent}%)\n"
                f"Disk: {disk.used/1e9:.1f}GB / {disk.total/1e9:.1f}GB\n"
                f"Uptime: {up}")
    except ImportError:
        r = subprocess.run(["systeminfo"], capture_output=True, text=True, timeout=15)
        lines = [l for l in r.stdout.splitlines() if any(k in l for k in ["OS","RAM","Memory"])]
        return "\n".join(lines[:6])

@mcp.tool()
def run_command(command: str) -> str:
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

@mcp.tool()
def read_file(path: str) -> str:
    """Read a file's contents."""
    p = Path(path).expanduser()
    if not p.exists():
        for base in [Path(os.path.expanduser("~/Desktop")),
                     Path(os.path.expanduser("~/Documents")), Path(".")]:
            if (base / path).exists():
                p = base / path; break
    if not p.exists(): return f"Not found: {path}"
    try:
        c = p.read_text(encoding="utf-8", errors="ignore")
        return c[:800] + "\n...(truncated)" if len(c) > 800 else c
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def list_files(location: str = "desktop") -> str:
    """List files in Desktop, Documents, or Downloads."""
    bases = {"desktop": os.path.expanduser("~/Desktop"),
             "documents": os.path.expanduser("~/Documents"),
             "downloads": os.path.expanduser("~/Downloads"),
             "current": "."}
    path = Path(bases.get(location.lower(), location))
    if not path.exists(): return f"Not found: {location}"
    items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
    lines = [f"Contents of {path}:\n"]
    for i in items[:30]:
        lines.append(f"  {'📁' if i.is_dir() else '📄'} {i.name}")
    return "\n".join(lines)

# ── CODE ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def write_code(filename: str, code: str) -> str:
    """Save code to Desktop/Nano_Projects/ and open in VS Code."""
    d = Path(os.path.expanduser("~/Desktop/Nano_Projects"))
    d.mkdir(exist_ok=True)
    p = d / filename
    p.write_text(code, encoding="utf-8")
    try:
        subprocess.Popen(["code", str(p)], shell=True)
    except Exception:
        os.startfile(str(p))
    return f"Saved {filename} ({code.count(chr(10))+1} lines) → {p}"

@mcp.tool()
def run_python_script(script_path: str) -> str:
    """Run a Python script and return its output."""
    p = Path(script_path).expanduser()
    if not p.exists():
        p = Path(os.path.expanduser("~/Desktop/Nano_Projects")) / script_path
    if not p.exists(): return f"Not found: {script_path}"
    try:
        r = subprocess.run([sys.executable, str(p)], capture_output=True,
                           text=True, timeout=30, encoding="utf-8", errors="replace")
        return (r.stdout or r.stderr or "No output").strip()
    except subprocess.TimeoutExpired:
        return "Timed out after 30s."
    except Exception as e:
        return f"Error: {e}"

# ── MEMORY ────────────────────────────────────────────────────────────────────

MEM = Path("data/memory/nano_memory.txt")
MEM.parent.mkdir(parents=True, exist_ok=True)

@mcp.tool()
def remember(fact: str) -> str:
    """Remember a fact for future conversations."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(MEM, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {fact}\n")
    return f"Remembered: {fact}"

@mcp.tool()
def recall(topic: str = "") -> str:
    """Recall stored memories."""
    if not MEM.exists(): return "No memories yet."
    lines = MEM.read_text(encoding="utf-8").strip().splitlines()
    if not lines: return "No memories yet."
    if topic: lines = [l for l in lines if topic.lower() in l.lower()]
    return "Memories:\n" + "\n".join(f"• {l}" for l in lines[-15:])

@mcp.tool()
def forget_all() -> str:
    """Clear all memories."""
    MEM.write_text("", encoding="utf-8")
    return "Memory cleared."

# ── PROMPTS ───────────────────────────────────────────────────────────────────

@mcp.prompt()
def explain_code(code: str) -> str:
    return f"Explain this code in simple English:\n\n```\n{code}\n```"

@mcp.prompt()
def fix_code(code: str, error: str) -> str:
    return f"Fix this code:\n```\n{code}\n```\nError: {error}"

@mcp.prompt()
def summarize(text: str) -> str:
    return f"Summarize in 3 bullet points:\n\n{text}"

# ── RUN ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "sse"
    print(f"\n[Nano MCP] Starting tool server on port 8001 ({transport})...")
    print("[Nano MCP] Tools: system, web, files, code, memory\n")
    if transport == "sse":
        mcp.run(transport="sse", host="0.0.0.0", port=8001)
    else:
        mcp.run(transport="stdio")