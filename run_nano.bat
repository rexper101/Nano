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
        print(f"  MCP Tools → http://localhost:8001  (run server.py)\n")

        # Greet
        self._speak("Hello Anike! I am Nano, ready to help.")

        if self.text_mode:
            print("  Type your command (Ctrl+C to quit)\n")
            self._text_loop()
        else:
            from stt.vad import VADDetector
            self.vad = VADDetector(
                on_speech_start=lambda: None,
                on_speech_end=self._on_audio,
                sensitivity=0.4,
            )
            self._set_state("listening")
            threading.Thread(target=self.vad.start,           daemon=True).start()
            threading.Thread(target=self._transcription_loop, daemon=True).start()
            print("  Speak to Nano!\n")
            while True:
                time.sleep(1)

    # ── Audio pipeline ────────────────────────────────────────────────────────

    def _on_audio(self, audio):
        if audio is not None and len(audio) > 8000:
            self.audio_queue.put(audio)

    def _transcription_loop(self):
        while True:
            if not self.audio_queue.empty():
                self._set_state("thinking")
                audio  = self.audio_queue.get()
                result = self.stt.transcribe(audio)
                text   = result.get("text", "").strip()
                if text and len(text) > 1:
                    asyncio.run(self._handle(text))
                else:
                    self._set_state("listening")
            time.sleep(0.05)

    def _text_loop(self):
        while True:
            try:
                text = input("\033[31mYou  : \033[0m").strip()
                if text:
                    asyncio.run(self._handle(text))
            except (KeyboardInterrupt, EOFError):
                print("\n\033[31mGoodbye!\033[0m")
                break

    # ── Core pipeline ─────────────────────────────────────────────────────────

    async def _handle(self, text: str):
        print(f"\033[32mYou  : {text}\033[0m")
        self._set_state("thinking")
        self._broadcast({"type": "thinking"})

        t0 = time.time()

        # 1. Call MCP tools
        tool_result = await self._call_tool(text)

        # 2. Build context
        context = text
        if tool_result:
            context = f"{text}\n\n[Tool result: {tool_result[:500]}]"
            print(f"\033[33mTool : {tool_result[:200]}\033[0m")

        # 3. LLM response
        self.history.append({"role": "user", "content": context})
        response = await self._llm(context)
        self.history.append({"role": "assistant", "content": response})
        if len(self.history) > 16:
            self.history = self.history[-16:]

        ms = int((time.time() - t0) * 1000)
        print(f"\033[31mNano : {response}\033[0m  \033[90m[{ms}ms]\033[0m\n")

        # 4. Broadcast to UI
        self._broadcast({
            "type":       "response",
            "response":   response,
            "action":     tool_result or "",
            "intent":     self._intent(text),
            "emotion":    self._emotion(response),
            "latency_ms": ms,
        })

        # 5. Speak
        self._set_state("speaking")
        self._speak(response)
        self._set_state("listening")

    # ── MCP Tool calling ──────────────────────────────────────────────────────

    async def _call_tool(self, text: str) -> str:
        """Detect intent and call the right MCP tool directly."""
        tl = text.lower().strip()

        # Add server.py directory to path so we can import it directly
        server_dir = os.path.dirname(os.path.abspath(__file__))
        if server_dir not in sys.path:
            sys.path.insert(0, server_dir)

        try:
            import server as tools

            # ── Time ──────────────────────────────────────────────────────
            if any(w in tl for w in ["what time","current time","what's the time",
                                      "date today","what day","what date"]):
                return tools.get_current_time()

            # ── Battery ───────────────────────────────────────────────────
            if "battery" in tl:
                return tools.get_battery_status()

            # ── System info ───────────────────────────────────────────────
            if any(w in tl for w in ["system info","cpu usage","ram usage","memory usage",
                                      "disk space","uptime","how much ram","check cpu"]):
                return tools.get_system_info()

            # ── CMD / run command ─────────────────────────────────────────
            cmd = self._extract_cmd(tl, text)
            if cmd:
                return tools.run_command(cmd)

            # ── Open app ──────────────────────────────────────────────────
            if re.search(r"\b(open|launch|start)\b", tl):
                app = self._extract_app(tl)
                if app:
                    return tools.open_application(app)

            # ── Play music ────────────────────────────────────────────────
            if re.search(r"\bplay\b", tl):
                q = re.sub(r"\b(play|on youtube|on spotify|song|music|track)\b", "", tl).strip()
                if q:
                    return tools.play_on_youtube(q)

            # ── Web search ────────────────────────────────────────────────
            SEARCH_WORDS = ["search","look up","find","what is","who is",
                            "news about","latest","tell me about","google"]
            if any(w in tl for w in SEARCH_WORDS):
                q = re.sub(r"\b(search for|look up|find|what is|who is|"
                           r"news about|latest news on|tell me about|google)\b",
                           "", tl).strip()
                return tools.search_web(q or text)

            # ── Get news ──────────────────────────────────────────────────
            if "news" in tl and not any(w in tl for w in ["news about","latest news"]):
                topic = re.sub(r"\b(news|latest|today|current)\b", "", tl).strip()
                return tools.get_news(topic or "technology")

            