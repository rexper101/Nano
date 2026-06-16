"""
Nano FastAPI Backend
=====================
Serves the chat UI and exposes REST + WebSocket endpoints
so ui/index.html can talk to the local Nano instance.

Run alongside main.py:
  python api_server.py          (in a second terminal)

Or let main.py start it automatically (default).

Endpoints:
  POST /chat          text → response
  WS   /ws            real-time chat
  GET  /health        system status
  GET  /memory        list memories
  GET  /workflows     list saved workflows
"""

import sys
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agents.router   import Router
from tts.japanese_speaker import NanoTTSSpeaker


SYSTEM_PROMPT = (
    "You are Nano, a cheerful and charming AI desktop assistant. "
    "You have a cute, playful personality — warm, witty, and slightly teasing. "
    "Keep replies under three sentences. Be direct and friendly."
)

# ── Global state ──────────────────────────────────────────────────────────────

class State:
    router   = None
    tts      = None
    history  = []

state = State()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Nano API] Starting up...")
    state.router = Router(system_prompt=SYSTEM_PROMPT)
    state.tts    = NanoTTSSpeaker()
    print("[Nano API] Ready ✓")
    yield
    print("[Nano API] Shutdown.")


app = FastAPI(title="Nano AI Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Serve UI files at /ui/
try:
    app.mount("/ui", StaticFiles(directory="ui"), name="ui")
except Exception:
    pass


# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    text:       str
    session_id: str = "default"


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Redirect to the UI."""
    return FileResponse("ui/index.html")


@app.post("/chat")
async def chat(req: ChatRequest):
    t0 = time.time()
    state.history.append({"role": "user", "content": req.text})

    loop     = asyncio.get_event_loop()
    response, action = await loop.run_in_executor(
        None,
        lambda: state.router.process(req.text, state.history)
    )

    state.history.append({"role": "assistant", "content": response})
    if len(state.history) > 20:
        state.history = state.history[-20:]

    return {
        "response":    response,
        "action":      action,
        "intent":      _detect_intent(req.text),
        "emotion":     _detect_emotion(response),
        "latency_ms":  int((time.time() - t0) * 1000),
    }


@app.get("/health")
async def health():
    import httpx
    ollama_ok = False
    try:
        r = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            ), timeout=3
        )
        ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {
        "status":  "ok" if ollama_ok else "degraded",
        "ollama":  ollama_ok,
        "avatar":  False,   # avatar runs in separate process
        "version": "3.0",
    }


@app.get("/memory")
async def memory():
    try:
        from tools.memory_tool import MemoryTool
        m   = MemoryTool()
        all = m._load_json() if hasattr(m, "_load_json") else []
        return {"memories": all, "count": len(all)}
    except Exception as e:
        return {"memories": [], "count": 0, "error": str(e)}


@app.get("/workflows")
async def workflows():
    from pathlib import Path
    import json
    lib = Path("data/recordings/library.json")
    if lib.exists():
        data = json.loads(lib.read_text())
        return {"workflows": list(data.values())}
    return {"workflows": []}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    print("[WS] Client connected")
    try:
        while True:
            raw  = await ws.receive_text()
            import json
            data = json.loads(raw)
            text = data.get("text", "").strip()
            if not text:
                continue

            await ws.send_json({"type": "thinking"})

            t0   = time.time()
            loop = asyncio.get_event_loop()
            response, action = await loop.run_in_executor(
                None,
                lambda: state.router.process(text, state.history)
            )
            state.history.append({"role": "user",      "content": text})
            state.history.append({"role": "assistant", "content": response})
            if len(state.history) > 20:
                state.history = state.history[-20:]

            await ws.send_json({
                "type":       "response",
                "response":   response,
                "action":     action,
                "intent":     _detect_intent(text),
                "emotion":    _detect_emotion(response),
                "latency_ms": int((time.time() - t0) * 1000),
            })

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["write","create app","build","generate","flask","html"]): return "code"
    if any(w in t for w in ["run","execute","command","install","git"]):              return "cmd"
    if any(w in t for w in ["open","close","launch"]):                                return "app"
    if any(w in t for w in ["cv","resume"]):                                          return "cv"
    if any(w in t for w in ["job","apply","linkedin"]):                               return "job"
    if any(w in t for w in ["email","gmail","reply","message"]):                      return "email"
    if any(w in t for w in ["search","look up","what is","news"]):                    return "search"
    if any(w in t for w in ["screen","screenshot","ocr"]):                            return "screen"
    if any(w in t for w in ["remember","memory","recall"]):                           return "memory"
    if any(w in t for w in ["file","folder","create file"]):                          return "file"
    return "chat"


def _detect_emotion(response: str) -> str:
    r = response.lower()
    if any(w in r for w in ["sorry","error","couldn't","failed","unfortunately"]): return "error"
    if any(w in r for w in ["created","done","saved","opened","found","success"]):  return "happy"
    if any(w in r for w in ["let me","thinking","analysing","checking"]):           return "thinking"
    return "idle"


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n\033[36m[Nano API] Starting on http://localhost:8000\033[0m")
    print("\033[36m[Nano API] Open dashboard: http://localhost:8000\033[0m\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
