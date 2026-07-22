"""
Nano TTS helper
===============

This module uses Edge TTS when available and falls back to the built-in
Windows speech engine if needed.
"""

import asyncio
import os
import re
import tempfile
import wave
from pathlib import Path

import numpy as np

ENGLISH_VOICES = [
    "en-US-AvaNeural",
    "en-US-JennyNeural",
    "en-GB-SoniaNeural",
]


class JapaneseTTSSpeaker:
    def __init__(self):
        self.voice = ENGLISH_VOICES[0]
        self.edge_available = self._check_edge_tts()
        if self.edge_available:
            print(f"[TTS] Edge TTS ready: {self.voice}")
        else:
            print("[TTS] Edge TTS unavailable. Using Windows built-in voice.")

    def _check_edge_tts(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    def synthesise(self, text: str) -> tuple:
        text = self._clean_text(text)
        if not text:
            return None, 0

        if self.edge_available:
            audio, rate = self._synthesise_with_edge(text)
            if audio is not None:
                return audio, rate

        self._speak_with_pyttsx3(text)
        return None, 0

    def _synthesise_with_edge(self, text: str) -> tuple:
        try:
            import edge_tts

            async def stream_audio():
                comm = edge_tts.Communicate(text, voice=self.voice, rate="+0%")
                buffer = b""
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        buffer += chunk["data"]
                return buffer

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                raw_mp3 = loop.run_until_complete(stream_audio())
            finally:
                loop.close()

            if not raw_mp3:
                return None, 0

            return self._decode_mp3(raw_mp3)
        except Exception as exc:
            print(f"[TTS] Edge TTS error: {exc}")
            return None, 0

 