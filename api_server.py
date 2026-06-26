"""
Nano API Server — Fast Mode
=============================
Uses phi3:mini for 2-3x faster responses.
Serves UI at http://localhost:8000
WebSocket at ws://localhost:8000/ws
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


class AppState:
    router  = None
    history = []

state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Nano] Loading...")
    try:
        from agents.system_prompt import SYSTEM_PROMPT
        from agents.router import Router
        state.router = Router(system_prompt=SYSTEM_PROMPT)
        print("[Nano] Ready ✓ — open http://localhost:8000 in Chrome")
    except Exception as e:
        print(f"[Nano] Startup error: {e}")
    yield


app = FastAPI(lifespan=lifespan)

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


@app.get("/", response_class=HTMLResponse)
async def root():
    p = Path("ui/index.html")
    if p.exists():
        return HTMLResponse(content=p.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>ui/index.html not found</h1>", status_code=404)


@app.get("/health")
async def health():
    import httpx
    ollama_ok = False
    model_used = "unknown"
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        models = [m["name"] for m in r.json().get("models", [])]
        ollama_ok  = True
        model_used = next((m for m in models if "phi3" in m), 
                     next((m for m in models if "qwen" in m), "none"))
    except Exception:
        pass
    return {
        "status":  "ok" if ollama_ok else "degraded",
        "ollama":  ollama_ok,
        "model":   model_used,
        "router":  state.router is not None,
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    if not state.router:
        return JSONResponse({"error": "Router not ready"}, status_code=503)

    t0 = time.time()
    state.history.append({"role": "user", "content": req.text})

    try:
        loop = asyncio.get_event_loop()
        response, action = await loop.run_in_executor(
            None, lambda t=req.text: state.router.process(t, state.history)
        )
    except Exception as e:
        response, action = f"Error: {e}", ""

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


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print(f"[WS] Client connected")
    try:
        while True:
            raw  = await ws.receive_text()
            data = json.loads(raw)
            text = data.get("text", "").strip()
            if not text:
                continue

            await ws.send_json({"type": "thinking"})

            if not state.router:
                await ws.send_json({
                    "type": "response",
                    "response": "Starting up — make sure Ollama is running: ollama serve",
                    "action": "", "intent": "error", "emotion": "error", "latency_ms": 0,
                })
                continue

            t0   = time.time()
            loop = asyncio.get_event_loop()

            try:
                response, action = await loop.run_in_executor(
                    None, lambda t=text: state.router.process(t, state.history)
                )
            except Exception as e:
                response, action = f"Error: {e}", ""

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
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


def _intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["write","create","build","generate","flask","html","script","code"]): return "code"
    if any(w in t for w in ["run","execute","install","git","ipconfig","pip","cmd","command"]):   return "cmd"
    if any(w in t for w in ["open","close","launch","start","play"]):                             return "app"
    if any(w in t for w in ["cv","resume"]):                                                      return "cv"
    if any(w in t for w in ["job","apply","linkedin"]):                                           return "job"
    if any(w in t for w in ["email","gmail","reply","inbox"]):                                    return "email"
    if any(w in t for w in ["search","news","what is","who is","look up"]):                       return "search"
    if any(w in t for w in ["screen","screenshot"]):                                              return "screen"
    if any(w in t for w in ["remember","memory","recall"]):                                       return "memory"
    return "chat"


