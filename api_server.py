"""
Nano API Server — v4 (fixed)
==============================
The backend NOW serves the frontend HTML directly at http://localhost:8000
This fixes the file:// → localhost CORS block completely.

Run:  python api_server.py
Then: open http://localhost:8000 in Chrome
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel


SYSTEM_PROMPT = (
    "You are Nano, a helpful AI desktop assistant. "
    "IMPORTANT: Always respond in English only — never use any other language. "
    "Keep replies under three sentences. Be direct, clear, and friendly. "
    "When you complete an action, confirm it in one short English sentence."
)


# ── App state ─────────────────────────────────────────────────────────────────
class AppState:
    router  = None
    history = []

state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Nano] Loading agents...")
    try:
        from agents.router import Router
        state.router = Router(system_prompt=SYSTEM_PROMPT)
        print("[Nano] Ready ✓  →  open http://localhost:8000")
    except Exception as e:
        print(f"[Nano] Router failed: {e}")
    yield


app = FastAPI(lifespan=lifespan)

# CORS — allow everything (needed for any direct file access too)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    text:       str
    session_id: str = "default"


# ── Serve the UI at root ──────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the frontend HTML — visit http://localhost:8000"""
    html_path = Path("ui/index.html")
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>ui/index.html not found</h1>", status_code=404)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    import httpx
    ollama_ok = False
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {
        "status":  "ok" if ollama_ok else "degraded",
        "ollama":  ollama_ok,
        "router":  state.router is not None,
    }


# ── Chat (REST fallback) ──────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    if not state.router:
        return JSONResponse({"error": "Router not ready"}, status_code=503)

    t0 = time.time()
    state.history.append({"role": "user", "content": req.text})

    loop = asyncio.get_event_loop()
    response, action = await loop.run_in_executor(
        None, lambda: state.router.process(req.text, state.history)
    )

    state.history.append({"role": "assistant", "content": response})
    if len(state.history) > 20:
        state.history = state.history[-20:]

    return {
        "response":   response,
        "action":     action or "",
        "intent":     _intent(req.text),
        "emotion":    _emotion(response),
        "latency_ms": int((time.time() - t0) * 1000),
    }


# ── WebSocket (real-time) ─────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    print("[WS] client connected")
    try:
        while True:
            raw  = await ws.receive_text()
            data = json.loads(raw)
            text = data.get("text", "").strip()
            if not text:
                continue

            # Send "thinking" immediately so UI shows dots
            await ws.send_json({"type": "thinking"})

            if not state.router:
                await ws.send_json({
                    "type":     "response",
                    "response": "Router not ready yet — please wait a moment.",
                    "action":   "", "intent": "error", "emotion": "error",
                    "latency_ms": 0,
                })
                continue

            t0   = time.time()
            loop = asyncio.get_event_loop()

            try:
                response, action = await loop.run_in_executor(
                    None, lambda: state.router.process(text, state.history)
                )
            except Exception as e:
                response = f"Something went wrong: {e}"
                action   = ""

            state.history.append({"role": "user",      "content": text})
            state.history.append({"role": "assistant", "content": response})
            if len(state.history) > 20:
                state.history = state.history[-20:]

            await ws.send_json({
                "type":       "response",
                "response":   response,
                "action":     action or "",
                "intent":     _intent(text),
                "emotion":    _emotion(response),
                "latency_ms": int((time.time() - t0) * 1000),
            })

    except WebSocketDisconnect:
        print("[WS] client disconnected")
    except Exception as e:
        print(f"[WS] error: {e}")
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ── Memory ────────────────────────────────────────────────────────────────────
@app.get("/memory")
async def get_memory():
    try:
        from tools.memory_tool import MemoryTool
        m = MemoryTool()
        facts = m._load_json()
        return {"memories": facts, "count": len(facts)}
    except Exception as e:
        return {"memories": [], "count": 0, "error": str(e)}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["write","create","build","generate","flask","html","script","app"]): return "code"
    if any(w in t for w in ["run","execute","command","install","git","pip"]):   return "cmd"
    if any(w in t for w in ["open","close","launch","start"]):                   return "app"
    if any(w in t for w in ["cv","resume"]):                                     return "cv"
    if any(w in t for w in ["job","apply","linkedin"]):                          return "job"
    if any(w in t for w in ["email","gmail","reply","inbox"]):                   return "email"
    if any(w in t for w in ["search","look up","news","what is","who is"]):      return "search"
    if any(w in t for w in ["screen","screenshot","ocr","what's on"]):           return "screen"
    if any(w in t for w in ["remember","memory","recall","forget"]):             return "memory"
    if any(w in t for w in ["file","folder","create file","create folder"]):     return "file"
    return "chat"


def _emotion(r: str) -> str:
    rl = r.lower()
    if any(w in rl for w in ["error","sorry","couldn't","failed","unable"]): return "error"
    if any(w in rl for w in ["done","created","saved","opened","success",
                              "completed","found","installed"]):              return "happy"
    if any(w in rl for w in ["let me","checking","searching","thinking"]):   return "thinking"
    return "idle"


# ── Start ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*48)
    print("  Nano API Server")
    print("  → http://localhost:8000  (open this in Chrome)")
    print("="*48 + "\n")
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,
    )
