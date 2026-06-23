"""
Nano API Server — FIXED
========================
Fixes:
  1. Serves HTML at http://localhost:8000
  2. WebSocket at ws://localhost:8000/ws
  3. Full CORS for all origins
  4. Returns action result separately so frontend can show it

Run:  python api_server.py
Then: open Chrome → http://localhost:8000
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel


SYSTEM_PROMPT = (
    "You are Nano, a helpful AI desktop assistant. "
    "ALWAYS respond in English only — never use any other language. "
    "Keep every reply under 3 sentences. Be direct, clear, and friendly. "
    "When you complete an action, confirm it in one short English sentence. "
    "Never output raw code in your spoken reply — describe what you did instead."
)


class AppState:
    router  = None
    history = []

state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Nano] Loading router...")
    try:
        from agents.router import Router
        state.router = Router(system_prompt=SYSTEM_PROMPT)
        print("[Nano] Router ready ✓")
    except Exception as e:
        print(f"[Nano] Router failed: {e}")
    print("[Nano] Open http://localhost:8000 in Chrome")
    yield


app = FastAPI(lifespan=lifespan)

# ── CORS — allow everything ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    text:       str
    session_id: str = "default"


# ── Serve UI at root ──────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    p = Path("ui/index.html")
    if p.exists():
        return HTMLResponse(content=p.read_text(encoding="utf-8"))
    return HTMLResponse("<h1 style='color:red'>ui/index.html not found — check your nano folder</h1>")


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


# ── Chat REST ─────────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    if not state.router:
        return JSONResponse({"error": "Router not ready. Is Ollama running?"}, status_code=503)

    t0 = time.time()
    state.history.append({"role": "user", "content": req.text})

    try:
        loop = asyncio.get_event_loop()
        response, action = await loop.run_in_executor(
            None, lambda: state.router.process(req.text, state.history)
        )
    except Exception as e:
        response = f"Error: {e}"
        action   = ""

    state.history.append({"role": "assistant", "content": response})
    if len(state.history) > 20:
        state.history = state.history[-20:]

    return {
        "response":   response,
        "action":     action or "",
        "intent":     _detect_intent(req.text),
        "emotion":    _detect_emotion(response),
        "latency_ms": int((time.time() - t0) * 1000),
    }


# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    client = ws.client.host if ws.client else "unknown"
    print(f"[WS] Client connected: {client}")

    try:
        while True:
            raw  = await ws.receive_text()
            data = json.loads(raw)
            text = data.get("text", "").strip()

            if not text:
                continue

            # Tell frontend we're thinking
            await ws.send_json({"type": "thinking"})

            if not state.router:
                await ws.send_json({
                    "type":     "response",
                    "response": "Nano is starting up. Make sure Ollama is running with: ollama serve",
                    "action":   "",
                    "intent":   "error",
                    "emotion":  "error",
                    "latency_ms": 0,
                })
                continue

            t0   = time.time()
            loop = asyncio.get_event_loop()

            try:
                response, action = await loop.run_in_executor(
                    None, lambda t=text: state.router.process(t, state.history)
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
                "intent":     _detect_intent(text),
                "emotion":    _detect_emotion(response),
                "latency_ms": int((time.time() - t0) * 1000),
            })

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {client}")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ── Helpers ───────────────────────────────────────────────────────────────────
def _detect_intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["write","create","build","generate","flask","html","script","app","code"]): return "code"
    if any(w in t for w in ["run","execute","command","install","pip","git","ipconfig","cmd"]):          return "cmd"
    if any(w in t for w in ["open","close","launch","start"]):                                           return "app"
    if any(w in t for w in ["cv","resume"]):                                                             return "cv"
    if any(w in t for w in ["job","apply","linkedin"]):                                                  return "job"
    if any(w in t for w in ["email","gmail","reply","inbox"]):                                           return "email"
    if any(w in t for w in ["search","look up","news","what is","who is"]):                              return "search"
    if any(w in t for w in ["screen","screenshot","ocr"]):                                               return "screen"
    if any(w in t for w in ["remember","memory","recall","forget"]):                                     return "memory"
    if any(w in t for w in ["file","folder","create file","create folder"]):                             return "file"
    return "chat"


def _detect_emotion(r: str) -> str:
    rl = r.lower()
    if any(w in rl for w in ["error","sorry","couldn't","failed","unable","not running"]): return "error"
    if any(w in rl for w in ["done","created","saved","opened","success","installed",
                              "completed","found","here is","here's"]):                    return "happy"
    if any(w in rl for w in ["let me","checking","searching","thinking","working"]):       return "thinking"
    return "idle"


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Nano API Server")
    print("  → http://localhost:8000")
    print("  → ws://localhost:8000/ws")
    print("="*50 + "\n")
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,
        ws_ping_interval=20,
        ws_ping_timeout=20,
    )