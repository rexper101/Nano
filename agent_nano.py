"""
Nano Voice Agent  —  agent_nano.py
=====================================
Add this to your nano folder alongside server.py.

Run:  python agent_nano.py --text    (text mode)
      python agent_nano.py           (voice mode)

Requires:
  - Ollama running:  ollama serve
  - MCP server:      python server.py  (in another terminal)
  - pip install mcp[cli] httpx faster-whisper sounddevice edge-tts soundfile
"""

import asyncio
import json
import os
import re
import sys
import time
import threading
import numpy as np
import sounddevice as sd
from queue import Queue
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
API_PORT   = 8000
MODEL      = "phi3:mini"   # fast — change to qwen2.5:7b for harder tasks

SYSTEM_PROMPT = """You are Nano, a powerful AI desktop assistant running on Windows.
You can run real terminal commands, write code, open apps, search the web,
manage files, and remember things.
Always reply in English only. Keep answers under 3 sentences.
When a tool runs, briefly say what you did. Address the user as Anike."""


class NanoAgent:

    def __init__(self, text_mode=False, no_avatar=False):
        self.text_mode   = text_mode
        self.no_avatar   = no_avatar
        self.history     = []
        self.audio_queue = Queue()
        self.avatar      = None
        self._ws_clients = set()
        self._banner()

    # ── Start ─────────────────────────────────────────────────────────────────

    def start(self):
        # STT
        print("  STT    : loading Whisper...", end=" ", flush=True)
        from stt.transcriber import Transcriber
        self.stt = Transcriber()
        print("ready ✓")

        # TTS
        print("  TTS    : loading voice...", end=" ", flush=True)
        from tts.japanese_speaker import JapaneseTTSSpeaker
        self.tts = JapaneseTTSSpeaker()
        print("ready ✓")

        # Avatar
        if not self.no_avatar:
            try:
                from avatar.anime_avatar import AnimeAvatarWindow
                self.avatar = AnimeAvatarWindow()
                self.avatar.start_in_thread()
                print("  Avatar : running ✓")
            except Exception as e:
                print(f"  Avatar : disabled ({e})")

        # Start API server (serves UI + WebSocket) in background
        threading.Thread(target=self._run_api, daemon=True).start()
        time.sleep(1.5)

        # Load user profile into system prompt
        profile = self._load_profile()
        self._system = SYSTEM_PROMPT + ("\n\nUser profile:\n" + profile if profile else "")

        print(f"\n  Dashboard → http://localhost:{API_PORT}")
        print(f"  MCP Tools → http://localhost:8001  (run server.py)
            # ── Recall ────────────────────────────────────────────────────
            if any(w in tl for w in ["what do you remember","recall","show memory",
                                      "what do you know","my memories"]):
                topic = re.sub(r"\b(what do you remember|recall|show memory|"
                               r"what do you know about|my memories)\b", "", tl).strip()
                return tools.recall(topic)

            # ── Forget ────────────────────────────────────────────────────
            if any(w in tl for w in ["forget everything","clear memory","delete memory"]):
                return tools.forget_all()

            # ── Run Python script ─────────────────────────────────────────
            m = re.search(r"run\s+([\w\-]+\.py)", tl)
            if m:
                return tools.run_python_script(m.group(1))

        except ImportError:
            # server.py not found — fall back to direct cmd execution
            cmd = self._extract_cmd(tl, text)
            if cmd:
                return self._run_direct(cmd)
        except Exception as e:
            return f"Tool error: {e}"

        return ""

    def _extract_cmd(self, tl: str, original: str) -> str:
        """Convert natural language to shell command."""
        # Direct run/execute
        m = re.match(r"^(?:run|execute|cmd|terminal)[:\s]+(.+)", original, re.IGNORECASE)
        if m: return m.group(1).strip()

        # pip
        m = re.search(r"pip\s+install\s+([\w\-\[\]\s,]+)", tl)
        if m: return f"pip install {m.group(1).strip()}"
        m = re.search(r"install\s+([\w\-\[\]]+)\s+(?:using|with|via)?\s*pip", tl)
        if m: return f"pip install {m.group(1)}"

        # git
        GIT = {"git status":"git status","git log":"git log --oneline -15",
               "git pull":"git pull","git push":"git push","git diff":"git diff",
               "git branch":"git branch -a"}
        for k, v in GIT.items():
            if k in tl: return v

        # system shortcuts
        if "ipconfig" in tl: return "ipconfig"
        if "disk space" in tl or "check disk" in tl:
            return "wmic logicaldisk get caption,freespace,size /format:list"
        if any(w in tl for w in ["tasklist","running processes","process list"]):
            return "tasklist"
        if "python version" in tl: return f'"{sys.executable}" --version'
        if "pip list" in tl or "installed packages" in tl: return "pip list"
        if "whoami" in tl: return "whoami"
        if "hostname" in tl: return "hostname"
        if any(w in tl for w in ["dir","list files","ls"]) and "create" not in tl:
            return "dir"
        m = re.search(r"ping\s+([\w\.\-]+)", tl)
        if m: return f"ping -n 4 {m.group(1)}"
        m = re.search(r"npm\s+(install|start|run|build|test)\s*(.*)", tl)
        if m: return f"npm {m.group(1)} {m.group(2)}".strip()

        return ""

    def _extract_app(self, text: str) -> str:
        APPS = ["chrome","firefox","vs code","vscode","code","notepad","calculator",
                "spotify","discord","explorer","terminal","word","excel","paint","vlc",
                "task manager","powershell","cmd","brave","zoom","teams","slack"]
        for app in sorted(APPS, key=len, reverse=True):
            if app in text: return app
        m = re.search(r"(?:open|launch|start)\s+([\w\s]+?)(?:\s+please|$)", text)
        return m.group(1).strip() if m else ""

    def _run_direct(self, command: str) -> str:
        """Run command directly without MCP server."""
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace", cwd=os.path.expanduser("~")
            )
            out = (r.stdout or r.stderr or "").strip()
            return out if out else f"Done: {command}"
        except Exception as e:
            return f"Error: {e}"

    # ── LLM ──────────────────────────────────────────────────────────────────

    async def _llm(self, text: str) -> str:
        import httpx
        messages = [{"role": "system", "content": self._system}]
        for msg in self.history[-8:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": text})
        try:
            resp = httpx.post(
                OLLAMA_URL,
                json={"model": MODEL, "messages": messages, "stream": False,
                      "options": {"temperature": 0.7, "num_predict": 200, "num_ctx": 2048}},
                timeout=45.0,
            )
            return resp.json()["message"]["content"].strip()
        except Exception as e:
            return f"Ollama error: {e}. Make sure Ollama is running: ollama serve"

    # ── TTS / Avatar ──────────────────────────────────────────────────────────

    def _speak(self, text: str):
        if self.avatar: self.avatar.start_speaking()
        audio, rate = self.tts.synthesise(text)
        if audio is not None:
            sd.play(audio, rate, blocking=True)
            time.sleep(0.2)
        if self.avatar: self.avatar.stop_speaking()

    def _set_state(self, state: str):
        if self.avatar: self.avatar.set_state(state)

    # ── FastAPI (serves UI + WebSocket) ───────────────────────────────────────

    def _run_api(self):
        import uvicorn
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import HTMLResponse

        api   = FastAPI()
        agent = self

        api.add_middleware(CORSMiddleware, allow_origins=["*"],
                           allow_methods=["*"], allow_headers=["*"])

        @api.get("/", response_class=HTMLResponse)
        async def root():
            p = Path(__file__).parent / "ui" / "index.html"
            if p.exists():
                return HTMLResponse(p.read_text(encoding="utf-8"))
            return HTMLResponse("<h1>ui/index.html not found</h1>")

        @api.get("/health")
        async def health():
            import httpx as hx
            try:
                r = hx.get("http://localhost:11434/api/tags", timeout=2.0)
                models = [m["name"] for m in r.json().get("models", [])]
                m = next((x for x in models if "phi3" in x),
                    next((x for x in models if "qwen" in x), "none"))
                return {"status":"ok","ollama":True,"model":m}
            except Exception:
                return {"status":"degraded","ollama":False,"model":"none"}

        @api.post("/chat")
        async def chat_rest(req: dict):
            text = req.get("text","").strip()
            if not text: return {"error":"empty"}
            t0   = time.time()
            tool = await agent._call_tool(text)
            ctx  = f"{text}\n\n[Tool: {tool}]" if tool else text
            agent.history.append({"role":"user","content":ctx})
            resp = await agent._llm(ctx)
            agent.history.append({"role":"assistant","content":resp})
            if len(agent.history) > 16: agent.history = agent.history[-16:]
            threading.Thread(target=agent._speak, args=(resp,), daemon=True).start()
            return {"response":resp,"action":tool or "",
                    "intent":agent._intent(text),"emotion":agent._emotion(resp),
                    "latency_ms":int((time.time()-t0)*1000)}

        @api.websocket("/ws")
        async def ws_ep(ws: WebSocket):
            await ws.accept()
            agent._ws_clients.add(ws)
            try:
                while True:
                    raw  = await ws.receive_text()
                    data = json.loads(raw)
                    text = data.get("text","").strip()
                    if not text: continue
                    await ws.send_json({"type":"thinking"})
                    t0   = time.time()
                    tool = await agent._call_tool(text)
                    ctx  = f"{text}\n\n[Tool: {tool}]" if tool else text
                    agent.history.append({"role":"user","content":ctx})
                    resp = await agent._llm(ctx)
                    agent.history.append({"role":"assistant","content":resp})
                    if len(agent.history) > 16: agent.history = agent.history[-16:]
                    msg = {"type":"response","response":resp,"action":tool or "",
                           "intent":agent._intent(text),"emotion":agent._emotion(resp),
                           "latency_ms":int((time.time()-t0)*1000)}
                    await ws.send_json(msg)
                    threading.Thread(target=agent._speak, args=(resp,), daemon=True).start()
            except WebSocketDisconnect:
                agent._ws_clients.discard(ws)
            except Exception:
                agent._ws_clients.discard(ws)

        uvicorn.run(api, host="0.0.0.0", port=API_PORT,
                    log_level="warning", ws_ping_interval=30,
                    ws_ping_timeout=60, out_keep_alive=65, )

    def _broadcast(self, msg: dict):
        dead = set()
        for ws in list(self._ws_clients):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(ws.send_json(msg))
                else:
                    loop.run_until_complete(ws.send_json(msg))
            except Exception:
                dead.add(ws)
        self._ws_clients -= dead

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_profile(self) -> str:
        p = Path(__file__).parent / "config" / "user_profile.txt"
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
        return ""

    def _intent(self, t: str) -> str:
        tl = t.lower()
        if any(w in tl for w in ["write","create","build","generate","flask","html","code","script"]): return "code"
        if any(w in tl for w in ["run","execute","install","git","ipconfig","pip","cmd"]):             return "cmd"
        if any(w in tl for w in ["open","launch","start","play"]):                                     return "app"
        if any(w in tl for w in ["search","news","what is","who is","look up"]):                       return "search"
        if any(w in tl for w in ["remember","memory","recall","forget"]):                              return "memory"
        if any(w in tl for w in ["file","folder","list files","read"]):                                return "file"
        return "chat"

    def _emotion(self, r: str) -> str:
        rl = r.lower()
        if any(w in rl for w in ["error","failed","sorry","unable","not running"]): return "error"
        if any(w in rl for w in ["done","created","saved","opened","installed","found"]): return "happy"
        return "idle"

    def _banner(self):
        print("\033[31m")
        print("  ╔══════════════════════════════════════════════╗")
        print("  ║     N A N O   A I   A G E N T   v 5 . 0    ║")
        print("  ║  MCP Tools · phi3:mini · Edge TTS · Free    ║")
        print("  ╚══════════════════════════════════════════════╝")
        print("\033[0m")


import subprocess

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--text",       action="store_true", help="Text mode, no mic")
    p.add_argument("--no-avatar",  action="store_true", help="No avatar window")
    args = p.parse_args()
    agent = NanoAgent(text_mode=args.text, no_avatar=args.no_avatar)
    agent.start()