"""
Nano — AI Desktop Assistant
=============================
VAD → Whisper STT → Ollama LLM → English TTS

Run:
  python main.py            voice mode
  python main.py --text     text mode (no mic)
  python main.py --no-avatar  no floating avatar
"""

import time
import threading
import sounddevice as sd
import numpy as np
from queue import Queue

from stt.transcriber      import Transcriber
from tts.japanese_speaker import JapaneseTTSSpeaker
from agents.router        import Router


SYSTEM_PROMPT = """You are Nano, a helpful AI desktop assistant.

RULES YOU MUST FOLLOW:
1. ALWAYS respond in English only — never use any other language.
2. Keep every reply SHORT — under 3 sentences maximum.
3. Be direct, friendly, and clear.
4. When you complete an action, briefly confirm what you did in one sentence.
5. Never output code blocks in your spoken reply — describe what you did instead.
6. Do not use markdown, bullet points, or special characters in your replies.
"""


class Nano:
    def __init__(self, text_mode=False, no_avatar=False):
        self._banner()
        self.text_mode   = text_mode
        self.history     = []
        self.audio_queue = Queue()
        self.avatar      = None

        # ── Avatar ────────────────────────────────────────────────────────
        if not no_avatar:
            try:
                from avatar.anime_avatar import AnimeAvatarWindow
                self.avatar = AnimeAvatarWindow()
                self.avatar.start_in_thread()
                print("  Avatar  : running ✓")
            except Exception as e:
                print(f"  Avatar  : disabled ({e})")

        # ── STT ───────────────────────────────────────────────────────────
        print("  STT     : loading Whisper...", end=" ", flush=True)
        self.stt = Transcriber()
        print("ready ✓")

        # ── TTS ───────────────────────────────────────────────────────────
        print("  TTS     : loading voice...", end=" ", flush=True)
        self.tts = JapaneseTTSSpeaker()
        print("ready ✓")

        # ── Router ────────────────────────────────────────────────────────
        print("  Agents  : ready ✓")
        self.router = Router(system_prompt=SYSTEM_PROMPT)

        # ── VAD ───────────────────────────────────────────────────────────
        if not text_mode:
            from stt.vad import VADDetector
            self.vad = VADDetector(
                on_speech_start=lambda: None,
                on_speech_end=self._on_audio,
                sensitivity=0.4,
            )

        self._show_ui_link()
        print("\n\033[31m  All systems online!\033[0m")
        print("\033[31m  " + ("Type below." if text_mode else "Speak to Nano!") + "\033[0m\n")

        self._speak("Hello! I am Nano, your AI desktop assistant. How can I help you?")

        if text_mode:
            self._text_loop()
        else:
            self._set("listening")
            threading.Thread(target=self.vad.start,           daemon=True).start()
            threading.Thread(target=self._transcription_loop, daemon=True).start()
            while True:
                time.sleep(1)

    # ── Avatar ────────────────────────────────────────────────────────────

    def _set(self, state):
        if self.avatar:
            self.avatar.set_state(state)

    # ── Audio pipeline ────────────────────────────────────────────────────

    def _on_audio(self, audio):
        if audio is not None and len(audio) > 8000:
            self.audio_queue.put(audio)

    def _transcription_loop(self):
        while True:
            if not self.audio_queue.empty():
                self._set("thinking")
                audio = self.audio_queue.get()
                result = self.stt.transcribe(audio)
                text   = result.get("text", "").strip()
                if text and len(text) > 1:
                    self._handle(text)
                else:
                    self._set("listening")
            time.sleep(0.05)

    def _text_loop(self):
        while True:
            try:
                text = input("\033[31mYou : \033[0m").strip()
                if text:
                    self._handle(text)
            except (KeyboardInterrupt, EOFError):
                print("\n\033[31mGoodbye!\033[0m")
                break

    # ── Core pipeline ─────────────────────────────────────────────────────

    def _handle(self, text):
        print(f"\033[32mYou  : {text}\033[0m")
        self._set("thinking")
        self.history.append({"role": "user", "content": text})

        response, action = self.router.process(text, self.history)

        if action:
            print(f"\033[33mAct  : {action[:200]}\033[0m")

        print(f"\033[31mNano : {response}\033[0m\n")
        self.history.append({"role": "assistant", "content": response})
        if len(self.history) > 20:
            self.history = self.history[-20:]

        self._set("speaking")
        self._speak(response)
        self._set("listening")
