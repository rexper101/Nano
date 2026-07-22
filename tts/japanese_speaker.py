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

    def _decode_mp3(self, mp3_bytes: bytes) -> tuple:
        try:
            import subprocess
            temp_mp3 = tempfile.mktemp(suffix=".mp3")
            temp_wav = tempfile.mktemp(suffix=".wav")
            with open(temp_mp3, "wb") as file:
                file.write(mp3_bytes)
            subprocess.run(
                ["ffmpeg", "-y", "-i", temp_mp3, "-ar", "22050", "-ac", "1", temp_wav],
                capture_output=True,
                timeout=10,
            )
            if os.path.exists(temp_wav):
                with wave.open(temp_wav, "rb") as wf:
                    rate = wf.getframerate()
                    frames = wf.readframes(wf.getnframes())
                os.unlink(temp_mp3)
                os.unlink(temp_wav)
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                return audio, rate
        except Exception:
            pass

        print("[TTS] MP3 decoding failed. Falling back to pyttsx3.")
        return None, 0

    def _speak_with_pyttsx3(self, text: str):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            for voice in voices:
                name = voice.name.lower()
                if any(keyword in name for keyword in ["zira", "hazel", "female", "eva"]):
                    engine.setProperty("voice", voice.id)
                    break
            engine.setProperty("rate", 165)
            engine.setProperty("volume", 1.0)
            engine.say(text)
            engine.runAndWait()
        except Exception as exc:
            print(f"[TTS] pyttsx3 error: {exc}")

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\[.*?\]", "", text)
        text = re.sub(r"\*\*?(.*?)\*\*?", r"\1", text)
        text = re.sub(r"`[^`]+`", "", text)
        text = re.sub(r"https?://\S+", "the link", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"⚡.*", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text if len(text) > 2 else ""
