"""
Nano — AI Desktop Assistant v3
================================
VAD → Whisper STT → Ollama LLM → Anime Character TTS
+ Anime girl avatar overlay
+ Full chat UI (ui/index.html)

Run:
  python main.py             full voice + avatar
  python main.py --text      text mode  (no mic)
  python main.py --no-avatar no avatar window
"""

import sys
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

import time
import threading
import socket
import sounddevice as sd
import numpy as np
from queue import Queue

from stt.vad             import VADDetector
from stt.transcriber     import Transcriber
from tts.japanese_speaker import NanoTTSSpeaker
from agents.router       import Router


SYSTEM_PROMPT = (
    "You are Nano, a cheerful and charming AI desktop assistant. "
    "You have a cute, playful personality — warm, witty, and slightly teasing. "
    "Speak naturally in clear English. Keep every reply under three sentences. "
    "You can write code, run commands, manage files, update CVs, "
    "apply for jobs, reply to emails, and search the web. "
    "When you finish an action, briefly confirm what you did."
)


class Nano:
    def __init__(self, text_mode=False, no_avatar=False):
        self._banner()
        self.text_mode   = text_mode
        self.history     = []
        self.audio_queue = Queue()
        self.avatar      = None

        # ── Anime avatar overlay ──────────────────────────────────────────
        if not no_avatar:
            try:
                from avatar.anime_avatar import AnimeAvatarWindow
                self.avatar = AnimeAvatarWindow()
                self.avatar.start_in_thread()
                print("  Avatar  : anime girl overlay running ✓")
            except Exception as e:
                print(f"  Avatar  : disabled ({e})")

        # ── STT ───────────────────────────────────────────────────────────
        print("  STT     : loading Whisper...", end=" ", flush=True)
        self.stt = Transcriber()
        print("ready ✓")

        # ── TTS (Anime character voice) ──────────────────────────────────
        print("  TTS     : loading Nano voice...", end=" ", flush=True)
        self.tts = NanoTTSSpeaker()
        print("ready ✓")

        # ── Router / agents ───────────────────────────────────────────────
        print("  Agents  : ready ✓")
        self.router = Router(system_prompt=SYSTEM_PROMPT)

        # ── Voice Activity Detection ──────────────────────────────────────
        if not text_mode:
            self.vad = VADDetector(
                on_speech_start=self._on_speech_start,
                on_speech_end=self._on_speech_end,
                sensitivity=0.4,
            )

        self._ui()
        print("\n\033[36m  All systems online!\033[0m")
        print("\033[36m  " + ("Type your command below." if text_mode
              else "Say something to Nano!") + "\033[0m\n")

        # Greeting
        greeting = "Hey there! I'm Nano, your personal AI assistant. What can I do for you today?"
        self._speak(greeting)

        if text_mode:
            self._text_loop()
        else:
            self._set("listening")
            threading.Thread(target=self.vad.start,           daemon=True).start()
            threading.Thread(target=self._transcription_loop, daemon=True).start()
            while True:
                time.sleep(1)

    # ── Avatar state helper ───────────────────────────────────────────────

    def _set(self, state):
        if self.avatar:
            self.avatar.set_state(state)

    # ── VAD callbacks ─────────────────────────────────────────────────────

    def _on_speech_start(self):
        pass

    def _on_speech_end(self, audio):
        if audio is not None and len(audio) > 8000:
            self.audio_queue.put(audio)

    # ── Transcription loop ────────────────────────────────────────────────

    def _transcription_loop(self):
        while True:
            if not self.audio_queue.empty():
                self._set("thinking")
                data = self.audio_queue.get()
                text = self.stt.transcribe(data).get("text", "").strip()
                if text and len(text) > 1:
                    self._handle(text)
                else:
                    self._set("listening")
            time.sleep(0.05)

    # ── Text loop ─────────────────────────────────────────────────────────

    def _text_loop(self):
        while True:
            try:
                text = input("\033[32mYou : \033[0m").strip()
                if text:
                    self._handle(text)
            except (KeyboardInterrupt, EOFError):
                print("\n\033[36mSayonara!\033[0m")
                break

    # ── Core pipeline ─────────────────────────────────────────────────────

    def _handle(self, text):
        print(f"\033[32mYou  : {text}\033[0m")
        self._set("thinking")
        self.history.append({"role": "user", "content": text})

        response, action = self.router.process(text, self.history)

        if action:
            print(f"\033[35mAct  : {action[:180]}\033[0m")

        print(f"\033[33mNano : {response}\033[0m\n")
        self.history.append({"role": "assistant", "content": response})
        if len(self.history) > 20:
            self.history = self.history[-20:]

        self._set("speaking")
        self._speak(response)
        self._set("listening")

    def _speak(self, text):
        if self.avatar:
            self.avatar.start_speaking()
        audio, rate = self.tts.synthesise(text)
        if audio is not None:
            sd.play(audio, rate, blocking=True)
            time.sleep(0.3)
        if self.avatar:
            self.avatar.stop_speaking()

    # ── Banner & UI hint ──────────────────────────────────────────────────

    def _banner(self):
        print("\033[36m")
        print("  ╔══════════════════════════════════════════╗")
        print("  ║   N  A  N  O   A  I   A  S  S  I  S  T ║")
        print("  ║   Nano Voice ✦ Offline ✦ Windows         ║")
        print("  ╚══════════════════════════════════════════╝")
        print("\033[0m")

    def _ui(self):
        import os
        ui = os.path.abspath("ui/index.html")

        # Try to start local API server (uvicorn) if port 8000 not in use
        def _port_open(host='127.0.0.1', port=8000):
            try:
                s = socket.socket()
                s.settimeout(0.4)
                s.connect((host, port))
                s.close()
                return True
            except Exception:
                return False

        if not _port_open():
            def _run_api():
                try:
                    import uvicorn
                    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, log_level="warning")
                except Exception as e:
                    print(f"  API: failed to start ({e})")
            threading.Thread(target=_run_api, daemon=True).start()

        print(f"\n  \033[36mDashboard → open in browser (or visit http://localhost:8000):\033[0m")
        print(f"  file:///{ui}\n")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--text",       action="store_true")
    p.add_argument("--no-avatar",  action="store_true")
    args = p.parse_args()
    Nano(text_mode=args.text, no_avatar=args.no_avatar)
